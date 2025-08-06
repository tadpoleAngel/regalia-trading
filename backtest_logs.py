import re

# Initialize variables
total_trades = 0
profitable_trades = 0
total_profit = 0

skipped = 0

filtered_trades = 0
filtered_profitable_trades = 0
filtered_profit = 0

# Define new rules
MAX_VOLATILITY = 500.0
MIN_DAILY_DROP = -7.0
MAX_DAILY_DROP = -5.0

# Regex patterns to extract data
trade_pattern = re.compile(r"Trade placed: Symbol=(\w+), Action=(\w+), Quantity=(\d+), Price=([\d.]+), Volatility=([\d.]+), Weekly Change=[\d.]+%, Daily Drop=(-[\d.]+)%")
position_pattern = re.compile(r"Position closed: Symbol=(\w+), Side=[\w.]+Entry Price=[\d.]+, Close Price=[\d.]+, Quantity=[\d.]+, Change=([-.\d]+), Change %=([-.\d]+)%")
# Store trades and results
trades = {}
results = {}
# biggest_change = 0
# biggest_change_symbol = ""
# Process the logs
with open("logs.txt", "r") as file:
    for line in file:
        # Match trade entries
        trade_match = trade_pattern.search(line)
        if trade_match:
            total_trades += 1
            symbol, action, quantity, price, volatility, daily_drop = trade_match.groups()
            symbol = symbol.strip().upper()  # Normalize symbol
            volatility = float(volatility)
            daily_drop = float(daily_drop)
            trades[symbol] = {"volatility": volatility, "daily_drop": daily_drop}
        
        # Match position closed entries
        position_match = position_pattern.search(line)
        if position_match:
            symbol, change, percent_change = position_match.groups()
            symbol = symbol.strip().upper()  # Normalize symbol
            change = float(change)
            # if float(percent_change.replace("%", "")) > biggest_change:
            #     biggest_change = float(percent_change.replace("%", ""))
            #     biggest_change_symbol = symbol
            total_profit += change
            if change > 0:
                profitable_trades += 1
            results[symbol] = change

# Apply new rules
for symbol, trade in trades.items():
    volatility = trade["volatility"]
    daily_drop = trade["daily_drop"]
    if volatility <= MAX_VOLATILITY and MIN_DAILY_DROP <= daily_drop <= MAX_DAILY_DROP:
        filtered_trades += 1
        if symbol in results:
            change = results[symbol]
            filtered_profit += change
            if change > 0:
                filtered_profitable_trades += 1
        else:
            print(f"Skipping {symbol} as it has no position closed entry.")
            skipped += 1

# Calculate accuracy
previous_accuracy = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
filtered_accuracy = (filtered_profitable_trades / filtered_trades) * 100 if filtered_trades > 0 else 0

# Print results
print("Previous Results:")
print(f"Total Trades: {total_trades}")
print(f"Profitable Trades: {profitable_trades}")
print(f"Accuracy: {previous_accuracy:.2f}%")
print(f"Total Profit: {total_profit:.2f}")

print("\nFiltered Results (New Rules):")
print(f"Total Trades: {filtered_trades}")
print(f"Profitable Trades: {filtered_profitable_trades}")
print(f"Accuracy: {filtered_accuracy:.2f}%")
print(f"Total Profit: {filtered_profit:.2f}")

print(f"Skipped Trades: {skipped}")

# print(f"Biggest change: {biggest_change} The symbol was {biggest_change_symbol}")