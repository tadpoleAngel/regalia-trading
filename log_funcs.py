import logging


logger = logging.getLogger(__name__)

class ExcludeWarningsFilter(logging.Filter):
    def filter(self, record):
        # Exclude specific warning messages
        return "sleep 3 seconds and retrying" not in record.getMessage()

# Apply to root so that I don't have to have all the rate limiting notifications
# in my log file
logging.getLogger().addFilter(ExcludeWarningsFilter())

logging.basicConfig(
    filename="logs.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_trade(symbol, action, quantity, current_close, volatility, week_change, drop):
    """
    Log details of a trade when it is placed.
    """
    logger.info(
        f"Trade placed: Symbol={symbol}, Action={action}, Quantity={quantity}, "
        f"Price={current_close:.2f}, Volatility={volatility:.2f}, "
        f"Weekly Change={week_change:.2f}%, Daily Drop={drop:.2f}%"
    )

def log_trade_result(symbol, side, entry_price: float, close_price: float, quantity):
    """
    Log the result of a trade when a position is closed.
    """
    profit_or_loss = (close_price - entry_price) * abs(quantity)
    percent_change = ((close_price - entry_price) / entry_price) * 100
    logger.info(
        f"Position closed: Symbol={symbol}, Side={side}" 
        f"Entry Price={entry_price:.2f}, "
        f"Close Price={close_price:.2f}, Quantity={quantity}, "
        f"Change={profit_or_loss:.2f}, "
        f"Change %={percent_change:.2f}%"
    )
