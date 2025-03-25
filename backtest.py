import yfinance as yf
import pandas as pd
import datetime
import sys
import alpaca_trade_api as tradeapi

API_KEY = 'PKY55WVYHH2MU9I0JLA9'
API_SECRET = 'qsPOIIZszQ2Y51CTgw1NLM6Ut7TeZGJE2CA8W3Fg'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# ----------------------------------------------------------------
# Trade Logic: uses daily open/high values injected into current_row.
# Now calculates trade quantity as 25% of total equity.
# ----------------------------------------------------------------
def trade_logic(symbol, current_row, historical_data, equity):
    """
    Determines whether to enter a trade for a given symbol on the current minute.
    Expects current_row to have the daily Open and High values (from the day's summary),
    while the minute's Close is used as the current price.
    
    Parameters:
      symbol (str): The ticker symbol.
      current_row (pd.Series): Current minute's data with keys 'Open', 'High', 'Close'.
      historical_data (pd.DataFrame): Historical daily data (prior days) with 'Open' and 'Close'.
      equity (float): Current total equity available.
    
    Returns:
      (action, quantity): 
          action (str): 'SELL' (to short) or 'BUY' (to go long) if conditions met, 'HOLD' otherwise.
          quantity (int): Number of shares to trade.
    """
    # --- Constants (tweak these as needed) ---
    MIN_VOLATILITY = 50.0           # Minimum annualized volatility in percent
    MIN_CHANGE_1W = 5.0             # Minimum weekly change in percent
    MIN_PERCENT_DROP_FROM_DAILY_HIGH = 0.05  # 5% drop
    MAX_PERCENT_DROP_FROM_DAILY_HIGH = 0.10  # 10% drop

    # Ensure values are scalars:
    try:
        current_close = float(current_row['Close'].iloc[0]) if hasattr(current_row['Close'], 'iloc') else float(current_row['Close'])
        current_high  = float(current_row['High'].iloc[0]) if hasattr(current_row['High'], 'iloc') else float(current_row['High'])
    except Exception as e:
        print(f"Error converting current_row values for {symbol}: {e}")
        return 'HOLD', 0

    # --- 1. Calculate annualized volatility using historical daily closes ---
    returns = historical_data['Close'].pct_change().dropna()
    if returns.empty:
        return 'HOLD', 0
    vol_std = returns.std()
    if hasattr(vol_std, 'iloc'):
        vol_std = vol_std.iloc[0]
    volatility = float(vol_std * (252 ** 0.5) * 100)
    if volatility < MIN_VOLATILITY:
        return 'HOLD', 0

    # --- 2. Calculate weekly change ---
    try:
        week_open = float(historical_data.iloc[0]['Open'].iloc[0]) if hasattr(historical_data.iloc[0]['Open'], 'iloc') else float(historical_data.iloc[0]['Open'])
    except Exception as e:
        print(f"Error converting historical_data open for {symbol}: {e}")
        return 'HOLD', 0
    week_change = ((current_close - week_open) / week_open) * 100
    if week_change < MIN_CHANGE_1W:
        return 'HOLD', 0

    # --- 3. Calculate drop from the daily high (using the injected daily high) ---
    drop = ((current_close - current_high) / current_high) * 100
    if drop < -(MAX_PERCENT_DROP_FROM_DAILY_HIGH * 100) or drop > -(MIN_PERCENT_DROP_FROM_DAILY_HIGH * 100):
        return 'HOLD', 0

    # --- 4. If conditions met, signal a SELL (short) order.
    # Calculate trade size as 25% of total equity.
    trade_amount = 0.25 * equity
    quantity = max(1, int(trade_amount / current_close))
    return 'SELL', quantity

# ----------------------------------------------------------------
# Backtesting function: intraday simulation with minute-level data.
# ----------------------------------------------------------------
def backtest(stocks, num_days, initial_balance):
    balance = initial_balance
    portfolio = {}  # positions per stock (can be negative for shorts)
    trade_history = []  # records of executed trades

    total_stocks = len(stocks)
    for s_idx, stock in enumerate(stocks):
        stock_progress = (s_idx + 1) / total_stocks * 100
        print(f"\nBacktesting {stock}... ({stock_progress:.2f}% complete)")
        try:
            daily_data = yf.download(stock, period=f'{num_days}d', interval='1d')
            if daily_data.empty:
                print(f"No daily data for {stock}, skipping.")
                continue

            for current_day in daily_data.index:
                day_str = current_day.strftime('%Y-%m-%d')
                minute_data = yf.download(stock, start=day_str, end=(current_day + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), interval='1m')
                if minute_data.empty:
                    print(f"No minute data for {stock} on {day_str}, skipping day.")
                    continue

                # Compute daily summary values:
                daily_open = float(minute_data.iloc[0]['Open'].iloc[0]) if hasattr(minute_data.iloc[0]['Open'], 'iloc') else float(minute_data.iloc[0]['Open'])
                daily_high = float(minute_data['High'].max().iloc[0]) if hasattr(minute_data['High'].max(), 'iloc') else float(minute_data['High'].max())
                hist_data = daily_data[daily_data.index < current_day]
                if hist_data.empty:
                    continue

                total_minutes = len(minute_data)
                for m_idx, (minute_time, row) in enumerate(minute_data.iterrows()):
                    modified_row = row.copy()
                    modified_row['Open'] = daily_open
                    modified_row['High'] = daily_high
                    # Pass current balance as equity.
                    action, quantity = trade_logic(stock, modified_row, hist_data, balance)
                    current_price = float(row['Close'].iloc[0]) if hasattr(row['Close'], 'iloc') else float(row['Close'])
                    
                    if action == 'BUY':
                        cost = current_price * quantity
                        if balance >= cost:
                            balance -= cost
                            portfolio[stock] = portfolio.get(stock, 0) + quantity
                            trade_history.append({
                                'Datetime': minute_time,
                                'Stock': stock,
                                'Action': 'BUY',
                                'Quantity': quantity,
                                'Price': current_price,
                                'Balance': balance
                            })
                            print(f"{minute_time} BUY {quantity} {stock} @ ${current_price:.2f}")
                        else:
                            print(f"{minute_time} Insufficient funds to BUY {stock}")
                    elif action == 'SELL':
                        balance += current_price * quantity
                        portfolio[stock] = portfolio.get(stock, 0) - quantity
                        trade_history.append({
                            'Datetime': minute_time,
                            'Stock': stock,
                            'Action': 'SELL',
                            'Quantity': quantity,
                            'Price': current_price,
                            'Balance': balance
                        })
                        print(f"{minute_time} SELL {quantity} {stock} @ ${current_price:.2f}")
                
                # End-of-day: Close any open positions using the last minute's close price.
                last_minute_time = minute_data.index[-1]
                closing_price = float(minute_data.iloc[-1]['Close'].iloc[0]) if hasattr(minute_data.iloc[-1]['Close'], 'iloc') else float(minute_data.iloc[-1]['Close'])
                if portfolio.get(stock, 0) != 0:
                    open_qty = portfolio.get(stock, 0)
                    if open_qty > 0:
                        balance += closing_price * open_qty
                        trade_history.append({
                            'Datetime': last_minute_time,
                            'Stock': stock,
                            'Action': 'CLOSE_LONG',
                            'Quantity': open_qty,
                            'Price': closing_price,
                            'Balance': balance
                        })
                        print(f"{last_minute_time} CLOSE_LONG {open_qty} {stock} @ ${closing_price:.2f}")
                    elif open_qty < 0:
                        balance -= closing_price * abs(open_qty)
                        trade_history.append({
                            'Datetime': last_minute_time,
                            'Stock': stock,
                            'Action': 'CLOSE_SHORT',
                            'Quantity': abs(open_qty),
                            'Price': closing_price,
                            'Balance': balance
                        })
                        print(f"{last_minute_time} CLOSE_SHORT {abs(open_qty)} {stock} @ ${closing_price:.2f}")
                    portfolio[stock] = 0

        except Exception as e:
            print(f"Error processing {stock}: {sys.exc_info()}")
    
    return balance, portfolio, trade_history

# ----------------------------------------------------------------
# Main: set parameters and run backtest
# ----------------------------------------------------------------
if __name__ == '__main__':
    num_days = 1  # Number of trading days to simulate (adjust as needed)
    stocks = [asset.symbol for asset in api.list_assets() if asset.tradable and asset.easy_to_borrow and asset.shortable and asset.status == 'active']
    initial_balance = 10000  # Starting cash
    final_balance, final_portfolio, history = backtest(stocks, num_days, initial_balance)
    
    df_history = pd.DataFrame(history)
    print("\nTrade History:")
    print(df_history)
    print("\nFinal Balance:", final_balance)
    print("Final Portfolio:", final_portfolio)
