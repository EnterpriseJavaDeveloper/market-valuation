import urllib.request as ul
import pandas as pd
import requests
from bs4 import BeautifulSoup as soup
from datetime import date

from caching import cache
from model.MarketData import MarketData


class MarketValueService:

    treasury_url = 'https://www.cnbc.com/quotes/US10Y'
    dividend_yield_url = 'https://www.multpl.com/s-p-500-dividend-yield'
    pe_ratio_url = 'https://www.multpl.com/s-p-500-pe-ratio'
    future_earnings_url = 'https://ycharts.com/indicators/sp_500_earnings_per_share_forward_estimate'

    @classmethod
    @cache.cached(timeout=86400, key_prefix='market_values')
    def download_market_values(cls):
        # Get Treasury yield from web
        page_soup = cls.get_page_soup(cls.treasury_url)
        treasury_yield = float(page_soup.find('span', {'class': 'QuoteStrip-lastPrice'}).contents[0][:-1])

        # Read dividend yield from web
        page_soup = cls.get_page_soup(cls.dividend_yield_url)
        div_yield = float(cls.get_web_data(page_soup)[:-1])

        # Read PE ratio from web
        page_soup = cls.get_page_soup(cls.pe_ratio_url)
        pe_ratio = float(cls.get_web_data(page_soup))

        return MarketData(pe_ratio, div_yield, treasury_yield)

    @classmethod
    def get_page_soup(cls, url):
        req = ul.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        client = ul.urlopen(req)
        htmldata = client.read()
        client.close()
        return soup(htmldata, "html.parser")

    @classmethod
    def get_web_data(cls, pagesoup):
        item_locator = pagesoup.find('div', id="current")
        return item_locator.contents[2].text.strip()

    @classmethod
    @cache.cached(timeout=86400, key_prefix='future_earnings')
    def download_future_earnings(cls):
        header = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        r = requests.get(cls.future_earnings_url, headers=header)
        df = pd.read_html(r.text)
        df_new = df[5].merge(df[6], how='outer')
        df_new['FormattedDate'] = pd.to_datetime(df_new['Date'])
        df_new = df_new.sort_values(by='FormattedDate')
        df_new = df_new.reset_index(drop=True)
        today = date.today()
        future_eps = 0
        counter = 0
        for index, row in df_new.iterrows():
            if row['FormattedDate'].date() > today and counter < 4:
                future_eps = future_eps + row['Value']
                counter = counter + 1
        max_eps = df_new.sort_values(by='FormattedDate', ascending=False).head(4)['Value'].sum()
        future_earnings = {'latest': future_eps, 'max': max_eps}
        return future_earnings
