import os
import torch
from torch.utils.data import DataLoader, random_split
from torch.nn import CrossEntropyLoss
from torch.optim import Adam
import matplotlib.pyplot as plt
from trade_model import TradeDecisionModel
from dataset import TradeDataset


def train_model(seed=42, epochs=20):
    torch.manual_seed(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = TradeDataset("logs.txt")

    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    train_set, test_set = random_split(dataset, [train_size, test_size])

    train_loader = DataLoader(train_set, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_set, batch_size=16, shuffle=False)

    model = TradeDecisionModel().to(device)
    pkl_path = 'regalai/regalai.pkl'
    if os.path.exists(pkl_path) and os.path.getsize(pkl_path) > 0:
        try:
            checkpoint = torch.load(pkl_path, map_location=device, weights_only=False)
            model.load_state_dict(checkpoint['model_state'])
            print("Loaded model weights from regalai/regalai.pkl")
        except Exception as e:
            print(f"Failed to load model weights from {pkl_path}: {e}\nTraining from scratch.")
    else:
        if os.path.exists(pkl_path):
            print(f"{pkl_path} exists but is empty. Training from scratch.")
        else:
            print("No existing model found. Training from scratch.")
    optimizer = Adam(model.parameters(), lr=0.001)
    criterion = CrossEntropyLoss()

    train_losses, test_losses, test_accuracies = [], [], []

    plt.ion()
    fig, ax = plt.subplots(2, 1, figsize=(8, 6))

    for epoch in range(epochs):
        model.train()
        total_train_loss = 0

        for X, y in train_loader:
            X, y = X.to(device), y.to(device)
            optimizer.zero_grad()
            output = model(X)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item()

        train_losses.append(total_train_loss / len(train_loader))

        model.eval()
        total_test_loss = 0
        correct, total = 0, 0
        with torch.no_grad():
            for X, y in test_loader:
                X, y = X.to(device), y.to(device)
                output = model(X)
                loss = criterion(output, y)
                total_test_loss += loss.item()
                preds = torch.argmax(output, dim=1)
                correct += (preds == y).sum().item()
                total += y.size(0)

        test_loss = total_test_loss / len(test_loader)
        accuracy = correct / total
        test_losses.append(test_loss)
        test_accuracies.append(accuracy)

        print(f"Epoch {epoch+1}: Train Loss={train_losses[-1]:.4f}, Test Loss={test_loss:.4f}, Accuracy={accuracy:.2%}")

        ax[0].clear()
        ax[1].clear()

        ax[0].plot(train_losses, label="Train Loss", color="blue")
        ax[0].plot(test_losses, label="Test Loss", color="red")
        ax[0].legend()
        ax[0].set_title("Loss")

        ax[1].plot(test_accuracies, label="Accuracy", color="green")
        ax[1].legend()
        ax[1].set_ylim(0, 1)
        ax[1].set_title("Accuracy")

        plt.pause(0.1)

    torch.save({
        'model_state': model.state_dict(),
        'model_class': TradeDecisionModel
    }, 'regalai/regalai.pkl')

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    train_model(epochs=2000)
