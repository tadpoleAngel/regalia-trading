import torch.nn as nn

class TradeDecisionModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 3)  # Outputs: 0 = no trade, 1 = long, 2 = short
        )

    def forward(self, x):
        return self.net(x)
