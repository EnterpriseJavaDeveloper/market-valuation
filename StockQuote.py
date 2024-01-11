import string
from datetime import datetime


class StockQuote(dict):
    open: float = 0
    high: float = 0
    low: float = 0
    close: float = 0
    # timestamp: string = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    def __init__(self, open, high, low, close):
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        dict.__init__(self, open=open, high=high, low=low, close=close, time=datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
