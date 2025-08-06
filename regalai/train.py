import torch
from torch.utils.data import DataLoader, random_split
from torch.nn import CrossEntropyLoss
from torch.optim import Adam
import matplotlib.pyplot as plt
from trade_model import TradeDecisionModel
from dataset import TradeDataset

# 🔁 Allow repeated experiments
def train_model(seed=42, epochs=20):
    torch.manual_seed(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = TradeDataset("logs.txt")

    print(f"Dataset size: {len(dataset)} samples")

    # 📊 Split into 80% train / 20% test
    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    train_set, test_set = random_split(dataset, [train_size, test_size])

    train_loader = DataLoader(train_set, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_set, batch_size=16, shuffle=False)

    model = TradeDecisionModel().to(device)
    optimizer = Adam(model.parameters(), lr=0.001)
    criterion = CrossEntropyLoss()

    train_losses, test_losses, test_accuracies = [], [], []

    # 📈 Live Plot Setup
    plt.ion()
    fig, ax = plt.subplots(2, 1, figsize=(8, 6))
    ax[0].set_title("Loss over Epochs")
    ax[1].set_title("Test Accuracy")

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

        # 🎯 Evaluation
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

        # 📉 Live Plot Updates
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

    # 🔐 Save final model
    torch.save({
        'model_state': model.state_dict(),
        'model_class': TradeDecisionModel
    }, 'trade_model.pkl')

    plt.ioff()
    plt.show()

if __name__ == "__main__":
    train_model()
