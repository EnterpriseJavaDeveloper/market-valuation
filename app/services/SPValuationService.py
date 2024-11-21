import json
import logging
from datetime import datetime, timedelta

from flask import Flask, request
from flask.logging import default_handler
from flask_apscheduler import APScheduler
# from flask_cors import Flask, request
# from flask_cors.logging import default_handler

from flask_marshmallow import Marshmallow
from dotenv import load_dotenv
import os

from app import SP_QUOTE, FUTURE_EARNINGS, MARKETDATA, SP_QUOTE_CALCULATED
from endpoints.AuthService import AuthService
from model.Earnings import Earnings
# from flask_socketio import SocketIO, emit
from flask_cors import cross_origin

from schema.earnings_schema import EarningsSchema
from app.services.FairMarketValueService import FairMarketValueService
from views import StockDataView

from app.services.MarketValueService import MarketValueService
from ShillerDataService import ShillerDataService
import collections

from StockQuoteService import StockQuoteService
from schema.coefficients_schema import CoefficientsSchema
from database import db
from caching import cache

# GSPC = 'GSPC'
#
collections.Iterable = collections.abc.Iterable
#
# SP_500 = 'SP500'
# FUTURE_EARNINGS = 'FUTUREEARNINGS'
# MARKETDATA = 'MARKETDATA'
# SP_QUOTE = 'SP500QUOTE'
# SP_QUOTE_CALCULATED = 'SP500QUOTECALCULATED'

app = Flask(__name__)
load_dotenv()
db_conn = ("postgresql+psycopg2://{user}:{password}@{hostname}/{database}"
           .format(user=os.environ.get('user'), password=os.environ.get('password'), hostname=os.environ.get('host')
                   , database=os.environ.get('database')))
app.config['SQLALCHEMY_DATABASE_URI'] = db_conn
db.init_app(app)
ma = Marshmallow(app)

root = logging.getLogger()
root.addHandler(default_handler)

app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['SECRET_KEY'] = 'secret!'
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_ECHO'] = True
# CORS(app)
cache.init_app(app)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

app.logger.setLevel(logging.INFO)


logging.basicConfig(level=logging.INFO)
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.INFO)
sqlalchemy_logger.addHandler(logging.StreamHandler())  # Ensure logging to console

STOCK_QUOTE_INTERVAL_TASK_ID = 'stock-quote-interval-task-id'
MARKET_DATA_INTERVAL_TASK_ID = 'market-data-interval-task-id'
VALUATION_INTERVAL_TASK_ID = 'valuation-interval-task-id'
FUTURE_VALUE_INTERVAL_TASK_ID = 'future-value-interval-task-id'
SAVE_FAIR_MARKET_DATA_TASK_ID = 'save-fair-market-data-task-id'
market_value_service = MarketValueService()
fair_market_value_service = FairMarketValueService()
stock_quote_service = StockQuoteService()

coefficients_schema = CoefficientsSchema(many=False)
earnings_schema = EarningsSchema(many=True)


def cache_quote():
    cache.set(SP_QUOTE, stock_quote_service.download_quote('^GSPC', '1d', '1m'))


def download_future_earnings():
    cache.set(FUTURE_EARNINGS, market_value_service.download_future_earnings())


def cache_market_values():
    cache.set(MARKETDATA, market_value_service.download_market_values())


def cache_calculated_stock_data():
    with app.app_context():
        cache.set(SP_QUOTE_CALCULATED, FairMarketValueService.calculate_fair_market_value())


def save_fair_market_value():
    with app.app_context():
        fair_market_value_service.save_fair_market_value()


with app.app_context():
    scheduler.add_job(id='stock_quote_startup', func=cache_quote, trigger='date', next_run_time=datetime.now())
    scheduler.add_job(id='market-data-startup-task-id', func=cache_market_values, trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=5))
    scheduler.add_job(id='calculated-stock-data-startup-task-id', func=cache_calculated_stock_data, trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=10))
    scheduler.add_job(id='future-earnings-startup-task-id', func=download_future_earnings, trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=15))
    scheduler.add_job(id='save-fair-market-value-startup-task-id', func=save_fair_market_value, trigger='date',
                      next_run_time=datetime.now() + timedelta(seconds=20))
    scheduler.add_job(id=STOCK_QUOTE_INTERVAL_TASK_ID, func=cache_quote, trigger='interval', seconds=60)
    scheduler.add_job(id=MARKET_DATA_INTERVAL_TASK_ID, func=cache_market_values, trigger='interval', hours=24)
    scheduler.add_job(id=FUTURE_VALUE_INTERVAL_TASK_ID, func=download_future_earnings, trigger='interval', hours=24)
    scheduler.add_job(id=VALUATION_INTERVAL_TASK_ID, func=cache_calculated_stock_data, trigger='interval', hours=24)
    scheduler.add_job(id=SAVE_FAIR_MARKET_DATA_TASK_ID, func=save_fair_market_value, trigger='interval', hours=24)
    ShillerDataService.initialize_shiller_data()


# http://127.0.0.1:5000/sp-data
app.add_url_rule('/sp-data', view_func=StockDataView.as_view('stock_data'))


@app.route('/valuation-data/<symbol>')
@cross_origin()
def get_valuation_data(symbol=None):
    dictionary = collections.OrderedDict()
    dictionary['stock_valuation'] = FairMarketValueService.calculate_fair_market_value()
    dictionary['market_data'] = MarketValueService.download_market_values()
    coefficients = coefficients_schema.dump(ShillerDataService.initialize_shiller_data().get('coefficients'))
    dictionary['equation_coefficients'] = coefficients  # Convert to dictionary
    dictionary['timestamp'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    return json.dumps(dictionary, indent=4)


@app.route('/quote/<symbol>')
@cross_origin()
def get_stock_quote(symbol=None):
    dictionary = collections.OrderedDict()
    if symbol == 'GSPC':
        dictionary['market_quote'] = stock_quote_service.download_quote('^GSPC', '1d', '1m')
    else:
        dictionary['market_quote'] = stock_quote_service.download_quote(symbol, '1d', '1m')
    return json.dumps(dictionary, indent=4)


@app.route('/historical-data/<symbol>')
@cross_origin()
def get_historical_data(symbol=None):
    dictionary = collections.OrderedDict()
    if symbol == GSPC:
        # Retrieve historical data
        historical_data = ShillerDataService.initialize_shiller_data().get('historicaldata')
        dictionary['price_fairvalue'] = historical_data

        # Retrieve last_date
        last_date_str = ShillerDataService.initialize_shiller_data().get('lastdate')

        if last_date_str:
            # Convert last_date to datetime object
            last_date = datetime.strptime(last_date_str, '%Y/%m/%d')
            # Query Earnings table for rows with event_time greater than last_date
            earnings = Earnings.query.filter(Earnings.event_time > last_date).all()

            # Filter earnings to ensure event_time month is greater than last_date month
            earnings = [e for e in earnings if e.event_time.month > last_date.month]

            # Group by month and year, and get the last row of each group
            from itertools import groupby
            from operator import attrgetter

            earnings.sort(key=attrgetter('event_time'))
            grouped_earnings = []
            for key, group in groupby(earnings, key=lambda x: (x.event_time.year, x.event_time.month)):
                last_row = list(group)[-1]
                grouped_earnings.append(last_row)

            # Convert event_time to YYYY/mm/dd format
            for earning in grouped_earnings:
                earning.event_time = earning.event_time.replace(day=1).strftime('%Y/%m/%d')

            # Convert to dictionary format
            earnings_schema = EarningsSchema(many=True)
            earnings_dict = earnings_schema.dump(grouped_earnings)

            # Add to dictionary
            dictionary['calculated_price_fairvalue'] = earnings_dict
    else:
        dictionary['price_fairvalue'] = stock_quote_service.download_quote(symbol, '1d', '1m')

    return json.dumps(dictionary, indent=4)


@app.route('/earnings/<symbol>')
@cross_origin()
def get_earnings(symbol=None):
    all_earnings = Earnings.query.all()
    results = earnings_schema.dumps(all_earnings)
    return results


@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    data = request.get_json()
    return AuthService.login(data)


# @cross_origin()
# @socketio.on('my event')
# def handle_my_custom_event(data):
#     emit('my response', data, broadcast=True)


# app.run(debug=False)
# if __name__ == '__main__':
#     app.run()
    # socketio.run(app)
