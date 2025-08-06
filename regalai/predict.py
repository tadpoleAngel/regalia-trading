import torch
from trade_model import TradeDecisionModel

def load_model(path='trade_model.pkl'):
    checkpoint = torch.load(path)
    model = checkpoint['model_class']()
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    return model

def predict_trade(model, price, volatility, week_change, drop):
    x = torch.tensor([[price, volatility, week_change, drop]], dtype=torch.float)
    logits = model(x)
    pred = torch.argmax(logits, dim=1).item() # May need to cast to int
    return {0: "No Trade", 1: "Long", 2: "Short"}[pred]
