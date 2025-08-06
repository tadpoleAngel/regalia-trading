import torch
from torch.utils.data import Dataset
from utils.log_parser import parse_logs

class TradeDataset(Dataset):
    def __init__(self, log_path="logs.txt"):
        data = parse_logs(log_path, return_unmatched=True)

        self.X = torch.tensor([
            [
                d["price"],
                d["volatility"],
                d["week_change"],
                d["drop"]
            ] for d in data
        ], dtype=torch.float32)

        self.y = torch.tensor([d["true_label"] for d in data], dtype=torch.long)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
