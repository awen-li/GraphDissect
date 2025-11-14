import os
import torch
import math
import time
import psutil
from collections import defaultdict
from .subgraph_logger import SubgraphLogger

class EmbeddingCache:
    def __init__(self):
        """Initialize an in-memory embedding cache mapping driver IDs to GNN embeddings."""
        self.cache = {}

    def get(self, driver_id):
        """Retrieve the cached embedding for a given driver ID."""
        return self.cache.get(driver_id, None)

    def update(self, driver_id, embedding):
        """Store a new embedding for a driver ID after detaching and moving to CPU."""
        self.cache[driver_id] = embedding.detach().cpu()


class DriftBasedScheduler:
    def __init__(self, trainer, learning_rate=0.01, drift_method='l2', disable_embed_drift=False, disable_fcov_drift=False):
        """
        Initialize the drift-based RL scheduler.

        Args:
            trainer: An object with `encode_graph(g)` that returns an embedding tensor.
            learning_rate: Learning rate for the optimizer.
            drift_method: Drift type (currently only 'l2' is implemented).
            disable_embed_drift: Whether to disable embedding drift feature for ablation.
            disable_fcov_drift: Whether to disable function coverage drift feature for ablation.
            
        """
        self.trainer = trainer
        self.embedding_cache = EmbeddingCache()
        self.drift_method = drift_method

        self.selection_count = defaultdict(int)
        self.coverage_cache = {}
        self.sg_logger = SubgraphLogger()

        # Ablation study flags
        self.disable_embed_drift = disable_embed_drift
        self.disable_fcov_drift = disable_fcov_drift

        self.init_weights = {
            "embed_drift": 0.1,
            #"frontier_count": 0.05,
            #"exclusive_num": 0.05,
            "fcov_drift": 0.3,
            #"edges": 0.05,
            
            #"crashes": 0.1,
            "crashes_drift": 0.2,
            "selection_penalty":0.2
        }

        # init spearate weights
        self._init_semantic_feature()
        self._init_fuzzing_feature()
        
        # overall weights
        self.weights = torch.nn.Parameter(torch.cat([
            self.semantic_weights,
            self.fuzzing_weights
        ], dim=0))
        
        self.optimizer = torch.optim.Adam([self.weights], lr=learning_rate)
        self.rewards = []  # stores (features, reward) tuples

    def _init_semantic_feature(self):
        self.semantic_features = []
        semantic_weights_list = []
        
        if not self.disable_embed_drift:
            self.semantic_features.append("embed_drift")
            semantic_weights_list.append(self.init_weights["embed_drift"])
        
        if not self.disable_fcov_drift:
            self.semantic_features.append("fcov_drift")
            semantic_weights_list.append(self.init_weights["fcov_drift"])
        
        # Always include selection penalty
        self.semantic_features.append("selection_penalty")
        semantic_weights_list.append(self.init_weights["selection_penalty"])
        
        self.semantic_weights = torch.nn.Parameter(torch.tensor(
            semantic_weights_list,
            dtype=torch.float
        ))

    def _init_fuzzing_feature(self):
        self.fuzzing_features = []
        fuzzing_weights_list = []
        
        # Always include crashes drift
        self.fuzzing_features.append("crashes_drift")
        fuzzing_weights_list.append(self.init_weights["crashes_drift"])
        
        self.fuzzing_weights = torch.nn.Parameter(torch.tensor(
            fuzzing_weights_list,
            dtype=torch.float
        ))

    def compute_embedding_drift(self, g, did):
        """
        Compute log-scaled L2 embedding drift between new and old embeddings.

        Returns:
            float: log1p(norm(h_new - h_old)) if h_old exists, else 0.0

        This compression prevents high drift values from dominating scores.
        """
        h_new = self.trainer.encode_graph(g).squeeze()
        h_old = self.embedding_cache.get(did)

        self.embedding_cache.update(did, h_new)

        if h_old is None:
            return 0.0

        embed_drift = torch.norm(h_new - h_old).item()
        return math.log1p(embed_drift)


    def compute_coverage_drift(self, g, did):
        """
        Compute log-scaled coverage drift as the fraction of changed function nodes.

        This measures how many nodes changed coverage status (increase or decrease)
        relative to the total number of functions in the subgraph.
        
        Returns:
            float: log1p(fraction of functions with changed coverage)
        """
        cover_counts = g.x[:, 0].tolist()
        func_ids = g.func_ids.tolist()
        cover_dict = dict(zip(func_ids, cover_counts))
        
        prev_dict = self.coverage_cache.get(did, {})
        coverage_drift = sum(
            #1 for fid in func_ids if cover_dict.get(fid, 0) != prev_dict.get(fid, 0)
            1 for fid in cover_dict if cover_dict[fid] > 0 and prev_dict.get(fid, 0) == 0
        )

        # Cache the current coverage
        self.coverage_cache[did] = cover_dict

        # Normalized by number of tracked functions
        return math.log1p(coverage_drift)

    def compute_selection_penalty(self, did, driver_ids):
        penalty = math.log1p(self.selection_count[did]) / math.log1p(len(driver_ids) + 1e-5)
        return penalty

        
    def analyze_subgraph(self, g):
        """
        Analyze subgraph features: count of total, frontier, and exclusive nodes.

        Returns a dictionary with the counts.
        """
        x = g.x
        total = x.size(0)
        frontier_scores = x[:, 4]
        frontier_count = int((frontier_scores > 0).sum().item())
        is_exclusive = x[:, 5]
        exclusive_num = int(is_exclusive.sum().item())
        return {
            "total": total,
            "exclusive_num": exclusive_num,
            "frontier_count": frontier_count
        }


    @torch.no_grad()
    def compute_driver_scores(self, wgraph_size, driver_ids, get_subgraph_fn, drv_runtime_stats):
        """
        Compute a score for each driver using normalized features and current RL weights.

        Args:
            wgraph_size (int): Total number of nodes in the whole call graph.
            driver_ids (List[int]): List of driver IDs.
            get_subgraph_fn (Callable): Function to fetch the subgraph for a given driver ID.

        Returns:
            Dict[int, float]: Mapping of driver ID to score.
        """
        scores = {}

        G_size = wgraph_size + 1e-5  # prevent divide-by-zero

        for did in driver_ids:
            g = get_subgraph_fn(did)
            if g is None or g.num_nodes == 0:
                scores[did] = 0.0
                continue
            
            ####################################################
            # semantic features
            ####################################################
            stats = self.analyze_subgraph(g)
            
            embed_drift = None
            fcov_drift = None

            semantic_features_list = []
            if not self.disable_embed_drift:
                # embedding drift: graph semantics
                embed_drift = self.compute_embedding_drift(g, did)
                semantic_features_list.append(embed_drift/G_size)
            if not self.disable_fcov_drift:
                # coverage drift: coverage involving
                fcov_drift = self.compute_coverage_drift(g, did)
                semantic_features_list.append(fcov_drift/G_size)
            # Always include selection penalty
            semantic_features_list.append(-self.compute_selection_penalty(did, driver_ids))

            semantic_features = torch.tensor(semantic_features_list, dtype=torch.float)

            
            ####################################################
            # fuzzing features
            ####################################################
            runtime = drv_runtime_stats.get(did, {})
            #edges        = math.log1p(runtime.get("edges", 0))
            
            

            #crashes      = math.log1p(runtime.get("crashes", 0))
            crashes_drift = math.log1p(runtime.get("delta_crashes", 0))

            fuzzing_features_list = []
            # Always include crashes drift
            fuzzing_features_list.append(crashes_drift)

            fuzzing_features = torch.tensor(fuzzing_features_list, dtype=torch.float)
            

            ####################################################
            # merging
            ####################################################
            features = torch.cat([semantic_features, fuzzing_features])
 

            score = torch.dot(self.weights, features)
            scores[did] = score.item()

            # Compute reward only from enabled features
            reward = crashes_drift  # Always include crashes drift
            if fcov_drift is not None:
                reward += fcov_drift
            
            self.rewards.append((features.detach(), reward))

            # -------- Logging --------
            semantic_drift_log = {}
            if embed_drift is not None:
                semantic_drift_log["embedding_drift"] = embed_drift/G_size
            if fcov_drift is not None:
                semantic_drift_log["fcov_drift"] = fcov_drift/G_size
            
            fuzzing_drift_log = {
                "delta_crashes": crashes_drift
            }
            
            
            self.sg_logger.log({
                "type": "driver_score",
                "driver_id": did,
                "subgraph_stats": {
                    "node_count": stats["total"],
                    "frontier_count": stats["frontier_count"],
                    "exclusive_count": stats["exclusive_num"]
                },
                "semantic_drift": semantic_drift_log,
                "fuzzing_drift": fuzzing_drift_log,
                "features": features.tolist(),
                "score": score.item()
            })

        return scores


    def compute_reinforce_loss(self, weights, rewards, features_list, clip_advantage=True, max_adv=1.0):
        """
        Compute REINFORCE loss with reward normalization and optional advantage clipping.

        Args:
            weights: The current policy weights.
            rewards: A list of scalar rewards.
            features_list: A list of feature tensors.
            clip_advantage: Whether to clip the advantage.
            max_adv: Maximum absolute value for advantage if clipping is enabled.

        Returns:
            Scalar loss tensor.
        """
        rewards_tensor = torch.tensor(rewards, dtype=torch.float)
        mean_r = rewards_tensor.mean()
        std_r = rewards_tensor.std(unbiased=False) + 1e-5

        loss = 0.0
        for i, features in enumerate(features_list):
            reward = rewards[i]
            norm_reward = (reward - mean_r) / std_r
            advantage = norm_reward

            if clip_advantage:
                advantage = max(min(advantage, max_adv), -max_adv)

            score = torch.dot(weights, features)
            if torch.isnan(score) or torch.isinf(score):
                print(f"[!] Skipping bad score at idx {i}: {score}")
                continue

            loss -= advantage * score

        return loss

    def update_policy(self):
        """
        Perform one REINFORCE policy update using collected features and rewards.

        Applies normalization, gradient clipping, and logs runtime and memory stats.
        """
        if not self.rewards:
            return

        start_time = time.time()
        torch.cuda.empty_cache()

        self.optimizer.zero_grad()

        features_list = [f for (f, _) in self.rewards]
        reward_list = [r for (_, r) in self.rewards]
        loss = self.compute_reinforce_loss(self.weights, reward_list, features_list)

        if torch.isnan(loss):
            print("[!] NaN loss encountered — skipping update.")
            return

        loss.backward()
        total_norm = torch.nn.utils.clip_grad_norm_([self.weights], max_norm=5.0)
        self.optimizer.step()

        elapsed_time = time.time() - start_time
        if torch.cuda.is_available():
            peak_memory = torch.cuda.max_memory_allocated() / (1024 ** 2)
        else:
            process = psutil.Process(os.getpid())
            peak_memory = process.memory_info().rss / (1024 ** 2)

        self.sg_logger.log({
            "type": "rl_update",
            "weights": {
                "semantic": {
                    name: float(value) for name, value in zip(self.semantic_features, self.semantic_weights.detach().cpu().tolist())
                },
                "fuzzing": {
                    name: float(value) for name, value in zip(self.fuzzing_features, self.fuzzing_weights.detach().cpu().tolist())
                }
            },
            "metrics": {
                "mean_reward": float(sum(reward_list) / len(reward_list)),
                "loss": float(loss.item()),
                "grad_norm": float(total_norm),
                "update_time_sec": float(elapsed_time),
                "peak_memory_MB": float(peak_memory) if peak_memory is not None else None
            }
        })

        if total_norm < 1e-3 and abs(loss.item()) < 1.0:
            print("[!] Learning may be saturated or stuck.")

        self.rewards.clear()

    def select_top_driver(self, wgraph_size, driver_ids, get_subgraph_fn, drv_runtime_stats, k=1):
        """
        Select the top-k scoring drivers using the current learned weights.

        Increments selection count and triggers a policy update.
        """
        scores = self.compute_driver_scores(wgraph_size, driver_ids, get_subgraph_fn, drv_runtime_stats)
        ranked = sorted(scores.items(), key=lambda x: -x[1])

        top_k = ranked[:k]
        for did, _ in top_k:
            self.selection_count[did] += 1

        self.update_policy()
        return top_k
