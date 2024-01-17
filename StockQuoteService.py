import yfinance as yf

from StockQuote import StockQuote
from flask import current_app


class StockQuoteService:

    @classmethod
    def download_quote(cls, tickers, period, interval):
        num_quotes = tickers.upper().split(',')
        size = len(num_quotes);
        data = yf.download(tickers=tickers, period=period, interval=interval)
        latest_quote = data.tail(1)
        if size == 1:
            stock_quote = StockQuote(latest_quote['Open'][0], latest_quote['High'][0], latest_quote['Low'][0],
                                 latest_quote['Close'][0])
        else:
            current_app.logger.info('more than 1, not yet supported')

        return stock_quote
