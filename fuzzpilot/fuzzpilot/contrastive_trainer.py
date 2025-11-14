import copy
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import DataLoader, Batch
from torch_geometric.nn import GCNConv, global_mean_pool

class CgEncoder(nn.Module):
    def __init__(self, in_dim=6, hidden_dim=32, out_dim=16):
        super().__init__()
        self.conv1 = GCNConv(in_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.head = nn.Sequential(nn.Linear(hidden_dim, out_dim), nn.ReLU())

    def forward(self, x, edge_index, batch):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        x = global_mean_pool(x, batch)
        return self.head(x)


class ContrastiveGraphTrainer:
    def __init__(self, in_dim=6, hidden_dim=32, out_dim=16, temperature=0.5, lr=1e-3, device='cpu'):
        self.device = device
        self.encoder = CgEncoder(in_dim, hidden_dim, out_dim).to(device)
        self.optimizer = torch.optim.Adam(self.encoder.parameters(), lr=lr)
        self.temperature = temperature

    def _nt_xent_loss(self, z1, z2):
        z1 = F.normalize(z1, dim=1)
        z2 = F.normalize(z2, dim=1)
        N = z1.size(0)
        z = torch.cat([z1, z2], dim=0)
        sim = torch.matmul(z, z.T) / self.temperature
        labels = torch.cat([torch.arange(N), torch.arange(N)]).to(z.device)
        mask = torch.eye(2 * N, dtype=torch.bool).to(z.device)
        sim = sim.masked_fill(mask, -1e9)
        loss = F.cross_entropy(sim, labels)
        return loss
    
    def graph_augmentation(self, data, drop_edge_rate=0.2, mask_feat_rate=0.3):
        aug = copy.deepcopy(data)
        num_edges = aug.edge_index.size(1)
        keep_indices = torch.randperm(num_edges)[:int((1 - drop_edge_rate) * num_edges)]
        aug.edge_index = aug.edge_index[:, keep_indices]

        num_nodes = aug.x.size(0)
        mask_nodes = random.sample(range(num_nodes), int(mask_feat_rate * num_nodes))
        aug.x[mask_nodes] = 0.0
        return aug

    def train_one_epoch(self, data_list, batch_size=32):
        self.encoder.train()
        dataloader = DataLoader(data_list, batch_size=batch_size, shuffle=True)
        total_loss = 0

        for batch in dataloader:
            # Unbatch into list of individual Data graphs
            data_list_batch = batch.to_data_list()

            # Skip graphs with no edges or no nodes
            data_list_batch = [
                g for g in data_list_batch
                if g.edge_index is not None and g.edge_index.size(1) > 0 and g.x is not None and g.x.size(0) > 0
            ]
            if not data_list_batch:
                continue

            # Apply graph augmentations
            batch1 = [self.graph_augmentation(d) for d in data_list_batch]
            batch2 = [self.graph_augmentation(d) for d in data_list_batch]

            # Re-batch the augmented graphs
            batch1 = Batch.from_data_list(batch1).to(self.device)
            batch2 = Batch.from_data_list(batch2).to(self.device)

            # Forward passes
            z1 = self.encoder(batch1.x, batch1.edge_index, batch1.batch)
            z2 = self.encoder(batch2.x, batch2.edge_index, batch2.batch)

            # Contrastive loss + optimizer step
            loss = self._nt_xent_loss(z1, z2)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss / len(dataloader) if len(dataloader) > 0 else 0.0


    def encode_graph(self, data):
        self.encoder.eval()
        data = data.to(self.device)
        with torch.no_grad():
            return self.encoder(data.x, data.edge_index, data.batch)

