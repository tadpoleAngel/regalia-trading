import os
import alpaca_trade_api as tradeapi
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import alpaca.common.exceptions
import pytz
import datetime as dt
from alpaca_trade_api import TimeFrame

#TO DO
#Change these functions to actually gather the last 
#five trading days instead of just the last five
#days

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
BASE_URL = 'https://paper-api.alpaca.markets'



api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
trading_client = TradingClient(API_KEY, API_SECRET, paper=True)


def get_last5Days_bars(_ticker):
    _timeNow = dt.datetime.now(pytz.timezone('US/Eastern'))
    _2DaysAgo = _timeNow - dt.timedelta(days=5) 


    _bars = api.get_bars(_ticker, TimeFrame.Day,
                         start=_2DaysAgo.isoformat(),
                         end=None,
                         limit=2
                         )
    return _bars


def get_week_open_price(symbol):
    bars = get_last5Days_bars(symbol).df#[symbol]
    
    week_open = bars.iloc[0]['open']
    return week_open

def calculate_week_change(symbol):
    week_open = get_week_open_price(symbol)
    # closes = api.get_bars(symbol, timeframe=, limit=1).df#['close']

    # if (closes.empty):
    #     return "Skip"

    # close = float(closes.iloc[0]['close'])
    # print(closes)
    # print(close)

    close = api.get_latest_quote(symbol).bp

    week_change = ((close - week_open) / week_open) * 100

    return week_change

def close_all_positions():
    """
    Close all open positions in the account. Continues even if some positions fail to close.
    
    Returns:
        tuple: (bool, dict) - (overall success, detailed results)
            - bool: True if all positions were closed successfully, False if any failed
            - dict: Dictionary with symbols as keys and their closing status/error as values
    """
    results = {}
    all_successful = True
    
    try:
        # Get all open positions
        positions = trading_client.get_all_positions()
        
        # Try to close each position
        for position in positions:
            try:
                trading_client.close_position(position.symbol)
                results[position.symbol] = "Closed successfully"
            except Exception as e:
                all_successful = False
                results[position.symbol] = f"Failed to close: {str(e)}"
                print(f"Error closing position {position.symbol}: {str(e)}")
                continue
        
        return all_successful, results
    except Exception as e:
        print(f"Error getting positions: {str(e)}")
        return False, {"error": f"Failed to get positions: {str(e)}"}

def get_drop_from_daily_high(symbol):
    """
    Calculate how far a stock has dropped from its daily high as a percentage.
    
    Args:
        symbol (str): The stock symbol to check
        
    Returns:
        float: Percentage drop (0 - 100) from daily high. Negative number indicates drop.
        None: If there's an error getting the data
    """
    try:
        # Get today's bar data
        today = dt.datetime.now(pytz.timezone('US/Eastern'))
        bars = api.get_bars(symbol, TimeFrame.Day,
                           start=today.strftime('%Y-%m-%d'),
                           end=None,
                           limit=1)
        
        if not bars or len(bars) == 0:
            return None
            
        daily_high = bars[0].h
        current_price = api.get_latest_quote(symbol).bp
        
        percentage_drop = ((current_price - daily_high) / daily_high) * 100
        return percentage_drop
        
    except Exception as e:
        print(f"Error calculating drop from daily high for {symbol}: {str(e)}")
        return None

def get_time_since_daily_high(symbol):
    """
    Calculate how long ago today's high occurred.
    
    Args:
        symbol (str): The stock symbol to check
        
    Returns:
        float: Minutes since the daily high
        None: If there's an error getting the data
    """
    try:
        # Get today's minute bars
        today = dt.datetime.now(pytz.timezone('US/Eastern'))
        bars = api.get_bars(symbol, TimeFrame.Minute,
                           start=today.strftime('%Y-%m-%d'),
                           end=None)
        
        if not bars or len(bars) == 0:
            return None
            
        # Find the bar with the highest price
        high_bar = max(bars, key=lambda x: x.h)
        high_time = high_bar.t
        
        # Calculate time difference
        current_time = dt.datetime.now(pytz.timezone('US/Eastern'))
        time_diff = current_time - high_time
        
        # Convert to minutes
        minutes_since_high = time_diff.total_seconds() / 60
        return minutes_since_high
        
    except Exception as e:
        print(f"Error calculating time since daily high for {symbol}: {str(e)}")
        return None

# print(close_all_positions())
# print(calculate_week_change('SPRC'))
# print(get_week_open_price('SPRC'))

# print(get_last5Days_bars('SPRC').df)
