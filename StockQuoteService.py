import yfinance as yf

from caching import cache
from model.StockQuote import StockQuote
from flask import current_app


class StockQuoteService:

    @classmethod
    @cache.cached(timeout=120, key_prefix='download_quote')
    def download_quote(cls, tickers, period, interval):
        num_quotes = tickers.upper().split(',')
        size = len(num_quotes);
        data = yf.download(tickers=tickers, period=period, interval=interval)
        latest_quote = data.tail(1)
        if size == 1:
            #Todo extract the values from the dataframe properly
            stock_quote = StockQuote(latest_quote['Open'].values[0][0], latest_quote['High'].values[0][0], latest_quote['Low'].values[0][0],
                                 latest_quote['Close'].values[0][0])
        else:
            current_app.logger.info('more than 1, not yet supported')

        return stock_quote
