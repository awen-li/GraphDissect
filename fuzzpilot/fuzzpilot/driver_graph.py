import torch
import dynsch
from torch_geometric.data import Data


class DriverGraph:
    def __init__(self):
        pass

    def syn_graphs(self):
        dynsch.synGraphs()

    def get_driver_subgraph(self, driver_id):
        node_dicts = dynsch.getSubgraphNodes(driver_id)  # List[Dict]
        edge_list  = dynsch.getSubgraphEdges(driver_id)  # List[Tuple[int, int]]

        if not node_dicts or len(node_dicts) == 0:
            return None

        # Sort nodes by funcId for consistent indexing
        node_dicts.sort(key=lambda d: d['funcId'])
        id_to_index = {d['funcId']: i for i, d in enumerate(node_dicts)}

        # Create tensor of funcIds for reuse
        func_ids = torch.tensor([d['funcId'] for d in node_dicts], dtype=torch.long)

        # Feature matrix (order: coverCount, callDepth, inDegree, outDegree, isFrontier, isExclusive)
        x = torch.tensor([
            [
                d.get('coverCount', 0),
                d.get('callDepth', 0),
                d.get('inDegree', 0),
                d.get('outDegree', 0),
                d.get('isFrontier', 0),
                d.get('isExclusive', 0),
            ]
            for d in node_dicts
        ], dtype=torch.float)

        # Build edge_index
        edge_index = torch.tensor([
            [id_to_index[src], id_to_index[dst]]
            for src, dst in edge_list
            if src in id_to_index and dst in id_to_index
        ], dtype=torch.long).t().contiguous()

        batch = torch.zeros(x.size(0), dtype=torch.long)

        # Return with func_ids field
        return Data(x=x, edge_index=edge_index, batch=batch, func_ids=func_ids)

