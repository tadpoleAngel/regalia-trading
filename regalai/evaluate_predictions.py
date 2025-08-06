from utils.log_parser import parse_logs
from trade_model import TradeDecisionModel
import torch

def label_to_str(label):
    return {0: "No Trade", 1: "Long", 2: "Short"}[label]

def evaluate():
    model = torch.load("regalai/regalai.pkl", weights_only=False)["model_class"]()
    model.load_state_dict(torch.load("regalai/regalai.pkl", weights_only=False)["model_state"])
    model.eval()

    trades = parse_logs("logs.txt")

    correct, total = 0, 0
    for t in trades:
        x = torch.tensor([[t["price"], t["volatility"], t["week_change"], t["drop"]]], dtype=torch.float)
        pred = torch.argmax(model(x)).item()
        actual = t["true_label"]
        match = pred == actual

        print(f"Trade: {t['line']}")
        print(f"→ Model Prediction: {label_to_str(pred)}")
        print(f"→ Actual Result: {label_to_str(actual)}")
        print(f"→ Match: {'✅' if match else '❌'}")
        print("-" * 60)

        correct += int(match)
        total += 1

    print(f"\n🎯 Accuracy: {correct}/{total} = {correct / total:.2%}")

if __name__ == "__main__":
    evaluate()
