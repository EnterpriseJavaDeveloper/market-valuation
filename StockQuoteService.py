import yfinance as yf

from StockQuote import StockQuote


class StockQuoteService:

    @classmethod
    def download_quote(cls, tickers, period, interval):
        data = yf.download(tickers=tickers, period=period, interval=interval)
        latest_quote = data.tail(1)
        stock_quote = StockQuote(latest_quote['Open'][0], latest_quote['High'][0], latest_quote['Low'][0],
                                 latest_quote['Close'][0])
        return stock_quote
