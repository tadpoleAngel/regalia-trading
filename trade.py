import pandas as pd
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta, time
import numpy as np
import pytz
import threading
import time as time_sleepy
import sys
import os
from types import SimpleNamespace
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import alpaca.common.exceptions
from alpaca_trade_api import TimeFrame
import requests
from ai_functions import close_all_positions
from freezegun import freeze_time

MIN_VOLATILITY = 50.0
PERCENT_TO_INVEST_PER_TRADE = 0.20
WIN_PERCENT = 10000.0
MIN_CHANGE_1W = 5.0
MIN_PERCENT_DROP_FROM_DAILY_HIGH = 0.05
MAX_PERCENT_DROP_FROM_DAILY_HIGH = 0.10
TRADING_START = time(10, 15)
TRADING_END = time(10, 35)

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
trading_client = TradingClient(API_KEY, API_SECRET, paper=True)

# ----------------------------------------------------------------
# New trade_logic function – trades 25% of available equity.
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
    MIN_VOLATILITY = 50.0           
    MIN_CHANGE_1W = 5.0             
    MIN_PERCENT_DROP_FROM_DAILY_HIGH = 0.05  
    MAX_PERCENT_DROP_FROM_DAILY_HIGH = 0.10  

    try:
        current_close = float(current_row['Close'].iloc[0]) if hasattr(current_row['Close'], 'iloc') else float(current_row['Close'])
        current_high  = float(current_row['High'].iloc[0])  if hasattr(current_row['High'], 'iloc') else float(current_row['High'])
    except Exception as e:
        print(f"Error converting current_row values for {symbol}: {e}")
        return 'HOLD', 0

    returns = historical_data['close'].pct_change().dropna()
    if returns.empty:
        return 'HOLD', 0
    vol_std = returns.std()
    if hasattr(vol_std, 'iloc'):
        vol_std = vol_std.iloc[0]
    volatility = float(vol_std * (252 ** 0.5) * 100)
    if volatility < MIN_VOLATILITY:
        return 'HOLD', 0

    try:
        week_open = float(historical_data.iloc[0]['open'].iloc[0]) if hasattr(historical_data.iloc[0]['open'], 'iloc') else float(historical_data.iloc[0]['open'])
    except Exception as e:
        print(f"Error converting historical_data open for {symbol}: {e}")
        return 'HOLD', 0
    week_change = ((current_close - week_open) / week_open) * 100
    if week_change < MIN_CHANGE_1W:
        return 'HOLD', 0

    drop = ((current_close - current_high) / current_high) * 100
    if drop < -(MAX_PERCENT_DROP_FROM_DAILY_HIGH * 100) or drop > -(MIN_PERCENT_DROP_FROM_DAILY_HIGH * 100):
        return 'HOLD', 0

    trade_amount = 0.25 * equity
    quantity = max(1, int(trade_amount / current_close))
    return 'SELL', quantity

# ----------------------------------------------------------------
# AssetCache and SingleAssetCache using Alpaca free tier data.
# ----------------------------------------------------------------
class AssetCache:
    def __init__(self):
        self.assets = {}
        self.bars_cache = {}
        self.quotes_cache = {}
        self.refresh()
    
    def refresh(self):
        self.assets = {asset.symbol: asset for asset in api.list_assets(status='active') if asset.tradable and asset.shortable}
        now = datetime.now(pytz.timezone('America/New_York'))
        end_time = now - timedelta(days=1)
        start_date = (end_time - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = end_time.strftime('%Y-%m-%d')
        
        for symbol in self.assets:
            try:
                for attempt in range(3):
                    try:
                        self.bars_cache[symbol] = api.get_bars(
                            symbol, 
                            TimeFrame.Day,
                            start=start_date,
                            end=end_date
                        )
                        break
                    except Exception as e:
                        if "subscription does not permit" in str(e):
                            print(f"Skipping {symbol} - no data access")
                            break
                if symbol in self.bars_cache and not self.bars_cache[symbol].df.empty:
                    last_bar = self.bars_cache[symbol].df.iloc[-1]
                    self.quotes_cache[symbol] = SimpleNamespace(bp=last_bar['close'])
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print("Cache Error", exc_type, fname, exc_tb.tb_lineno, symbol, e)

    def get_asset(self, symbol):
        return self.assets.get(symbol)
    
    def get_bars(self, symbol):
        return self.bars_cache.get(symbol)
    
    def get_quote(self, symbol):
        return self.quotes_cache.get(symbol)
    
    def is_shortable(self, symbol):
        asset = self.get_asset(symbol)
        return asset and asset.shortable and asset.easy_to_borrow and asset.marginable

class SingleAssetCache:
    def __init__(self, symbol):
        self.symbol = symbol
        self.asset = None
        self.bars = None
        self.quote = None
        self.refresh()
    
    def refresh(self):
        try:
            assets = {asset.symbol: asset for asset in api.list_assets(status='active') if asset.tradable and asset.shortable}
            self.asset = assets.get(self.symbol)
            if not self.asset:
                return
            
            now = datetime.now(pytz.timezone('America/New_York'))
            end_time = now - timedelta(days=1)
            start_date = (end_time - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = end_time.strftime('%Y-%m-%d')
            
            self.bars = api.get_bars(
                self.symbol, 
                TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            if self.bars and not self.bars.df.empty:
                last_bar = self.bars.df.iloc[-1]
                self.day_open = SimpleNamespace(bp=last_bar['open'])
                self.day_high = SimpleNamespace(bp=last_bar['high'])
                self.quote = SimpleNamespace(bp=last_bar['close'])
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("Cache Error", exc_type, fname, exc_tb.tb_lineno, self.symbol, e)
    
    def is_shortable(self):
        return (self.asset and self.asset.shortable and 
                self.asset.easy_to_borrow and self.asset.marginable)

def calculate_sleep_time(time_to_wake_up: time):
    now = datetime.now()
    target = datetime.combine(now.date(), time_to_wake_up)
    if now.time() > time_to_wake_up:
        target += timedelta(days=1)
    return (target - now).total_seconds()

myEquity = 0.0
stop_script = False
errors = []
insufficient_funds = False

def check_open_position(symbol):
    global insufficient_funds, errors
    try:
        closes = api.get_bars(symbol, '1Min', limit=1).df
        close = float(closes.iloc[0]['close'])
        entry_price = float(api.get_position(symbol).avg_entry_price)
        win_price = entry_price - (entry_price * (WIN_PERCENT / 100.0))
        if close <= win_price:
            api.close_position(symbol)
            print('Closed', symbol)
            insufficient_funds = False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno, symbol, e)
        errors.append((exc_type, fname, exc_tb.tb_lineno, symbol))

def input_listener():
    global stop_script
    input("Press Enter to terminate the script normally...\n")
    stop_script = True
    print("terminating...")

def urgent_listener():
    global errors
    userInput = ""
    while userInput != "now":
        userInput = input("Type \"now\" and press enter to terminate the script immediately...\n")
    print("terminating now...")
    print("script terminated.\n")
    print("Exceptions: ")
    print(errors)
    os._exit(os.EX_OK)

def main():
    global stop_script, errors, insufficient_funds, myEquity
    assets = {asset.symbol: asset for asset in api.list_assets(status='active') if asset.tradable and asset.shortable}
    myEquity = float(api.get_account().equity)
    print("Starting main loop...")
    while not stop_script:
        for symbol in assets.keys():
            try:
                asset_cache = SingleAssetCache(symbol)
                
                try:
                    position_size = api.get_position(symbol)
                    position_size = float(position_size.qty)
                except tradeapi.rest.APIError as e:
                    if e.code == 40410000:
                        position_size = 0.0
                    else:
                        raise(e)
                
                if position_size != 0:
                    check_open_position(symbol)
                    continue
                
                if not (TRADING_START <= datetime.now().time() <= TRADING_END):
                    time_to_wake_up = TRADING_START
                    sleep_seconds = calculate_sleep_time(time_to_wake_up)
                    print(f"It's {datetime.now().time()}, I'll just nap until it's time for me to place some trades.")
                    print(f"\nSleeping until {time_to_wake_up} EST...")
                    unclosed_positions = len(trading_client.get_all_positions()) > 0
                    while sleep_seconds > 1:
                        if time(16, 1) < datetime.now().time() < time(16, 3) and unclosed_positions:
                            print(f"\nIt's {datetime.now().time()} and I've got open positions!")
                            print("Closing all open positions...")
                            print(close_all_positions())
                            unclosed_positions = False
                            insufficient_funds = False

                        if time(17, 1) < datetime.now().time() < time(17, 3):
                            print("Restarting script...")
                            os.execv(sys.executable, ['python'] + sys.argv)
                        hours = int(sleep_seconds // 3600)
                        minutes = int((sleep_seconds % 3600) // 60)
                        seconds = int(sleep_seconds % 60)
                        print(f"\rTime until I wake up: {hours:02d}:{minutes:02d}:{seconds:02d}", end="")
                        time_sleepy.sleep(1)
                        sleep_seconds = calculate_sleep_time(time_to_wake_up)
                    myEquity = float(api.get_account().equity)
                    print(f"\nI'm waking up to place some trades, my current equity is {myEquity}")
                
                if insufficient_funds:
                    continue
                if not asset_cache.is_shortable():
                    continue
                
                # Build current_row from free tier data (T+1):
                try:
                    current_row = pd.Series({
                        'Open': asset_cache.day_open.bp,
                        'High': asset_cache.day_high.bp,
                        'Close': asset_cache.quote.bp
                    })
                except Exception as e:
                    print(f"Error building current_row for {symbol}: {e}")
                    continue
                
                historical_data = asset_cache.bars.df
                action, quantity = trade_logic(symbol, current_row, historical_data, myEquity)
                if action == 'HOLD':
                    continue
                
                market_order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.SELL if action == 'SELL' else OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
                
                try:
                    market_order = trading_client.submit_order(order_data=market_order_data)
                    print('Opened', symbol, action, quantity)
                except alpaca.common.exceptions.APIError as e:
                    if e.code == 40310000:
                        print('Insufficient funds, skipping symbols with no open positions')
                        insufficient_funds = True
                    else:
                        raise(e)
            
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno, symbol, e)
                errors.append((exc_type, fname, exc_tb.tb_lineno, symbol))
    
def check_open_position(symbol):
    global insufficient_funds, errors
    try:
        closes = api.get_bars(symbol, '1Min', limit=1).df
        close = float(closes.iloc[0]['close'])
        entry_price = float(api.get_position(symbol).avg_entry_price)
        win_price = entry_price - (entry_price * (WIN_PERCENT / 100.0))
        if close <= win_price:
            api.close_position(symbol)
            print('Closed', symbol)
            insufficient_funds = False
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno, symbol, e)
        errors.append((exc_type, fname, exc_tb.tb_lineno, symbol))
        
if __name__ == '__main__':
    listener_thread = threading.Thread(target=input_listener)
    listener_thread.start()
    urgent_thread = threading.Thread(target=urgent_listener)
    urgent_thread.daemon = True
    urgent_thread.start()
    main()

print("script terminated.\n")
print("Exceptions:")
print(errors)
