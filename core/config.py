# Phase 1 MVP Configuration

# Limit the stock universe to S&P 500 or Nasdaq 100 to ensure API stability,
# algorithm correctness, and dashboard stability before scaling up.

UNIVERSE = "SP500"  # Options: "SP500" or "NASDAQ100"

# This is a sample subset for testing purposes.
# In the actual implementation, this will be dynamically fetched or populated.
SP500_SAMPLE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", 
    "META", "BRK.B", "TSLA", "UNH", "JNJ"
]

NASDAQ100_SAMPLE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", 
    "META", "TSLA", "AVGO", "PEP", "COST"
]

def get_universe_tickers():
    """Returns the list of tickers for the active MVP universe."""
    if UNIVERSE == "SP500":
        return SP500_SAMPLE
    elif UNIVERSE == "NASDAQ100":
        return NASDAQ100_SAMPLE
    else:
        return []
