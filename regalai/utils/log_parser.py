import re

def parse_logs(file_path, profit_threshold=1.0, return_unmatched=False):
    trade_pattern = re.compile(
        r"Trade placed: Symbol=(.*?), Action=(.*?), Quantity=(.*?), Price=(.*?), "
        r"Volatility=(.*?), Weekly Change=(.*?), Daily Drop=(.*)"
    )
    result_pattern = re.compile(
        r"Position closed: Symbol=(.*?), Side=(.*?)Entry Price=(.*?), "
        r"Close Price=(.*?), Quantity=(.*?), Change=(.*?), Change %=(.*)"
    )

    trades = []
    results = []
    with open(file_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        t = trade_pattern.search(line)
        r = result_pattern.search(line)

        if t:
            trades.append({
                "symbol": t.group(1).strip(),
                "action": t.group(2).lower().strip(),
                "quantity": float(t.group(3)),
                "price": float(t.group(4)),
                "volatility": float(t.group(5)),
                "week_change": float(t.group(6).replace('%', '')),
                "drop": float(t.group(7).replace('%', '')),
                "line": line.strip(),
                "matched": False,
                "true_label": 0
            })

        elif r:
            results.append({
                "symbol": r.group(1).strip(),
                "side": r.group(2).lower().strip(),
                "entry_price": float(r.group(3)),
                "close_price": float(r.group(4)),
                "quantity": float(r.group(5)),
                "profit": float(r.group(6)),
                "change_pct": float(r.group(7).replace('%', ''))
            })

    labeled = []
    used_results = set()

    for trade in trades:
        match = None
        for i, result in enumerate(results):
            if i in used_results:
                continue
            if result["symbol"] == trade["symbol"]:
                match = result
                used_results.add(i)
                break

        if match is None:
            if return_unmatched:
                labeled.append(trade)
            continue

        long_profit = (match["close_price"] - match["entry_price"]) * match["quantity"]
        short_profit = (match["entry_price"] - match["close_price"]) * match["quantity"]

        if long_profit > profit_threshold and long_profit > short_profit:
            label = 1  # long
        elif short_profit > profit_threshold:
            label = 2  # short
        else:
            label = 0  # no trade

        labeled.append({
            "symbol": trade["symbol"],
            "price": trade["price"],
            "volatility": trade["volatility"],
            "week_change": trade["week_change"],
            "drop": trade["drop"],
            "true_label": label,
            "entry_price": match["entry_price"],
            "close_price": match["close_price"],
            "change_pct": match["change_pct"],
            "profit": match["profit"],
            "side": match["side"],
            "line": trade["line"]
        })

    return labeled

if __name__ == "__main__":
    logs = parse_logs("logs.txt")
    print("Parsed logs:")
    for log in logs:
        print(log)
    # Optionally save to CSV or process further
