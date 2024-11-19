# app/__init__.py
from datetime import datetime, timedelta, date

import pandas as pd
import requests
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from flask_caching import Cache
from flask_apscheduler import APScheduler

from app.schemas.coefficients_schema import CoefficientsSchema
from app.schemas.earnings_schema import EarningsSchema
from app.services import MarketValueService, FairMarketValueService
from app.services.ShillerDataService import ShillerDataService
from app.services.StockQuoteService import StockQuoteService

# Initialize extensions
db = SQLAlchemy()
ma = Marshmallow()
cache = Cache()
scheduler = APScheduler()

GSPC = 'GSPC'
SP_500 = 'SP500'
FUTURE_EARNINGS = 'FUTUREEARNINGS'
MARKETDATA = 'MARKETDATA'
SP_QUOTE = 'SP500QUOTE'
SP_QUOTE_CALCULATED = 'SP500QUOTECALCULATED'

coefficients_schema = CoefficientsSchema(many=False)
earnings_schema = EarningsSchema(many=True)

def cache_quote(app):
    with app.app_context():
        cache.set(SP_QUOTE, StockQuoteService.download_quote('^GSPC', '1d', '1m'))

def download_future_earnings():
    header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    r = requests.get(MarketValueService.future_earnings_url, headers=header)
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

def cache_market_values(app):
    with app.app_context():
        cache.set(MARKETDATA, MarketValueService.download_market_values())

def cache_calculated_stock_data(app):
    with app.app_context():
        cache.set(SP_QUOTE_CALCULATED, FairMarketValueService.calculate_fair_market_value())

def save_fair_market_value(app):
    with app.app_context():
        FairMarketValueService.save_fair_market_value()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize extensions with app
    db.init_app(app)
    ma.init_app(app)
    cache.init_app(app)  # Ensure cache is initialized with app
    scheduler.init_app(app)
    CORS(app)

    # Register blueprints or routes
    from views import stock_data_view
    app.register_blueprint(stock_data_view)
    from app.views.SPValuationView import bp as sp_valuation_bp
    app.register_blueprint(sp_valuation_bp)

    STOCK_QUOTE_INTERVAL_TASK_ID = 'stock-quote-interval-task-id'
    MARKET_DATA_INTERVAL_TASK_ID = 'market-data-interval-task-id'
    VALUATION_INTERVAL_TASK_ID = 'valuation-interval-task-id'
    FUTURE_VALUE_INTERVAL_TASK_ID = 'future-value-interval-task-id'
    SAVE_FAIR_MARKET_DATA_TASK_ID = 'save-fair-market-data-task-id'

    # Add scheduled task
    scheduler.add_job(id='stock_quote_startup', func=cache_quote, args=[app], trigger='date', next_run_time=datetime.now())
    scheduler.add_job(id='market-data-startup-task-id', func=cache_market_values, args=[app], trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=5))
    scheduler.add_job(id='calculated-stock-data-startup-task-id', func=cache_calculated_stock_data, args=[app], trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=10))
    scheduler.add_job(id='future-earnings-startup-task-id', func=download_future_earnings, trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=15))
    scheduler.add_job(id='save-fair-market-value-startup-task-id', func=save_fair_market_value, args=[app], trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=20))
    scheduler.add_job(id=STOCK_QUOTE_INTERVAL_TASK_ID, func=cache_quote, args=[app], trigger='interval', seconds=60)
    scheduler.add_job(id=MARKET_DATA_INTERVAL_TASK_ID, func=cache_market_values, args=[app], trigger='interval', hours=24)
    scheduler.add_job(id=FUTURE_VALUE_INTERVAL_TASK_ID, func=download_future_earnings, trigger='interval', hours=24)
    scheduler.add_job(id=VALUATION_INTERVAL_TASK_ID, func=cache_calculated_stock_data, args=[app], trigger='interval', hours=24)
    scheduler.add_job(id=SAVE_FAIR_MARKET_DATA_TASK_ID, func=save_fair_market_value, args=[app], trigger='interval', hours=24)
    ShillerDataService.initialize_shiller_data(app)
    scheduler.start()

    return app