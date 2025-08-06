import torch
from torch.utils.data import Dataset
import re

class TradeDataset(Dataset):
    def __init__(self, log_path, profit_threshold=1.0):
        self.samples = []
        self._parse_logs(log_path, profit_threshold)

    def _parse_logs(self, path, profit_threshold):
        trades, results = [], []

        with open(path, 'r') as f:
            lines = f.readlines()

        trade_pattern = re.compile(
            r"Trade placed: Symbol=(.*?), Action=(.*?), Quantity=(.*?), Price=(.*?), Volatility=(.*?), Weekly Change=(.*?), Daily Drop=(.*)"
        )
        result_pattern = re.compile(
            r"Position closed: Symbol=(.*?), Side=(.*?),Entry Price=(.*?), Close Price=(.*?), Quantity=(.*?), Change=(.*?), Change %=(.*)"
        )

        open_trades = {}

        for line in lines:
            trade_match = trade_pattern.search(line)
            result_match = result_pattern.search(line)

            if trade_match:
                t = {
                    "symbol": trade_match.group(1),
                    "action": trade_match.group(2),
                    "quantity": float(trade_match.group(3)),
                    "price": float(trade_match.group(4)),
                    "volatility": float(trade_match.group(5)),
                    "week_change": float(trade_match.group(6)),
                    "drop": float(trade_match.group(7))
                }
                open_trades[t["symbol"]] = t  # Overwrites same-symbol entries

            elif result_match:
                r = {
                    "symbol": result_match.group(1),
                    "side": result_match.group(2).lower(),
                    "entry_price": float(result_match.group(3)),
                    "close_price": float(result_match.group(4)),
                    "quantity": float(result_match.group(5)),
                    "change_pct": float(result_match.group(7))
                }
                if r["symbol"] in open_trades:
                    t = open_trades.pop(r["symbol"])
                    features = torch.tensor([
                        t["price"], t["volatility"], t["week_change"], t["drop"]
                    ], dtype=torch.float)

                    # Label assignment
                    if r["change_pct"] > profit_threshold:
                        label = 1 if r["side"] == "long" else 2
                    else:
                        label = 0
                    self.samples.append((features, label))

        # Add remaining trades as 'no trade' (0)
        for t in open_trades.values():
            features = torch.tensor([
                t["price"], t["volatility"], t["week_change"], t["drop"]
            ], dtype=torch.float)
            self.samples.append((features, 0))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]
