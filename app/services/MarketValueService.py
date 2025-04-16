import re
import urllib.request as ul
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup as soup
from datetime import date, datetime

from app.shared.caching import cache
from app.models.MarketData import MarketData


class MarketValueService:

    treasury_url = 'https://www.cnbc.com/quotes/US10Y'
    dividend_yield_url = 'https://www.multpl.com/s-p-500-dividend-yield'
    dividend_url = 'https://www.multpl.com/s-p-500-dividend'
    dividend_growth_url = 'https://www.multpl.com/s-p-500-dividend-growth'
    pe_ratio_url = 'https://www.multpl.com/s-p-500-pe-ratio'
    earnings_url = 'https://ycharts.com/indicators/sp_500_earnings_per_share_forward_estimate'

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

        # Read dividend from web
        page_soup = cls.get_page_soup(cls.dividend_url)
        dividend, dividend_timestamp = cls.get_web_data(page_soup, get_timestamp=True)
        dividend = float(dividend)

        # Read dividend growth from web
        page_soup = cls.get_page_soup(cls.dividend_growth_url)
        dividend_growth, dividend_growth_timestamp = cls.get_web_data(page_soup, get_timestamp=True)
        dividend_growth = float(dividend_growth[:-1])
        print(f"dividend growth timestamp: {dividend_growth_timestamp} dividend timestamp: {dividend_timestamp}")

        return MarketData(pe_ratio, div_yield, treasury_yield, dividend, dividend_timestamp, dividend_growth, dividend_growth_timestamp)

    @classmethod
    def get_page_soup(cls, url):
        req = ul.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        client = ul.urlopen(req)
        htmldata = client.read()
        client.close()
        return soup(htmldata, "html.parser")

    @classmethod
    def get_web_data(cls, pagesoup, get_timestamp=False):
        item_locator = pagesoup.find('div', id="current")
        if get_timestamp:
            # Extract the timestamp
            timestamp_locator = pagesoup.find('div', id="timestamp")
            ts = timestamp_locator.contents[0].text.strip()
            # Extract the date using regex
            match = re.search(r"([A-Za-z]+\s\d{4})", ts)
            if match:
                extracted_date = match.group(1)
                # Convert to a date object
                date_object = datetime.strptime(extracted_date, "%b %Y").date()
                print(date_object)
            else:
                print("No valid date found.")
            return item_locator.contents[2].text.strip(), date_object
        return item_locator.contents[2].text.strip()

    @classmethod
    @cache.cached(timeout=86400, key_prefix='future_earnings')
    def download_future_earnings(cls):
        header = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        r = requests.get(cls.earnings_url, headers=header)
        df = pd.read_html(StringIO(r.text))
        df_new = df[5].merge(df[6], how='outer')
        df_new['FormattedDate'] = pd.to_datetime(df_new['Date'])
        df_new = df_new.sort_values(by='FormattedDate')
        df_new = df_new.reset_index(drop=True)
        today = date.today()

        future_eps = 0
        counter = 0
        latest_date = None

        # Filter rows before and after today
        before_today = df_new[df_new['FormattedDate'].dt.date < today]
        after_today = df_new[df_new['FormattedDate'].dt.date > today]

        # Get the trailing earnings
        trailing_values = before_today['Value'].tail(4)
        trailing_date = before_today['FormattedDate'].max().date()
        trailing_earnings = trailing_values.sum()

        # Get the last two values before today and the first two values after today
        blended_before = before_today.tail(2)
        blended_after = after_today.head(2)

        # Calculate the blended earnings by summing the selected values
        blended_earnings = blended_before['Value'].sum() + blended_after['Value'].sum()

        # Get the max date for the blended earnings
        blended_date = blended_after['FormattedDate'].max().date()

        # Filter out future earnings
        for index, row in df_new.iterrows():
            if row['FormattedDate'].date() > today and counter < 4:
                future_eps += row['Value']
                counter += 1
                latest_date = row['FormattedDate'].date()  # Update latest_date

        max_eps = df_new.sort_values(by='FormattedDate', ascending=False).head(4)['Value'].sum()
        max_date = df_new['FormattedDate'].max().date()

        earnings = {'trailing': trailing_earnings, 'trailing_date': trailing_date, 'future': future_eps, 'future_date': latest_date, 'max': max_eps, 'max_date': max_date,
                           'blended': blended_earnings, 'blended_date': blended_date}
        return earnings
