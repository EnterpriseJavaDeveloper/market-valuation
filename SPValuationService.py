import json
import pickle
import logging
from datetime import datetime

from flask import Flask
from flask_apscheduler import APScheduler
from flask.logging import default_handler

from sqlalchemy import func, and_
from flask_marshmallow import Marshmallow
from dotenv import load_dotenv
import os

from model.Coefficients import Coefficients
from model.Earnings import Earnings
from FairMarketValueService import FairMarketValueService
# from flask_socketio import SocketIO, emit
from flask_cors import cross_origin
from shared_resources import calculate_fair_market_value
from views import StockDataView

from MarketValueService import MarketValueService
from ShillerDataService import ShillerDataService
import collections

from StockQuoteService import StockQuoteService
from schema.coefficients_schema import CoefficientsSchema
from database import db

GSPC = 'GSPC'

collections.Iterable = collections.abc.Iterable

SP_500 = 'SP500'
FUTURE_EARNINGS = 'FUTUREEARNINGS'
MARKETDATA = 'MARKETDATA'
SP_QUOTE = 'SP500QUOTE'
SP_QUOTE_CALCULATED = 'SP500QUOTECALCULATED'

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

# CORS(app)
app.cache = {}
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
app.config['SECRET_KEY'] = 'secret!'
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_ECHO'] = True
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


class EarningsSchema(ma.Schema):
    class Meta:
        fields = (
        'id', 'calculated_earnings', 'calculated_price', 'future_earnings', 'blended_earnings', 'max_earnings',
        'future_price', 'blended_price', 'max_price', 'treasury_yield', 'dividend', 'current_price', 'event_time')


earnings_schema = EarningsSchema(many=True)


def cache_quote():
    app.cache[SP_QUOTE] = stock_quote_service.download_quote('^GSPC', '1d', '1m')


def download_future_earnings():
    app.cache[FUTURE_EARNINGS] = market_value_service.download_future_earnings()


def cache_market_values():
    app.cache[MARKETDATA] = market_value_service.download_market_values()


def save_fair_market_value():
    stock_data = app.cache.get(MARKETDATA)
    coefficient_data = pickle.load(open('ml_model_regression.pkl', 'rb'))  # TODO get regression data from database
    stock_quote_data = app.cache.get(SP_QUOTE)
    future_earnings_data = app.cache.get(FUTURE_EARNINGS)
    with app.app_context():
        # TODO don't save more than once a day
        stock_valuation = fair_market_value_service.calculate_fair_market_value(stock_data, coefficient_data,
                                                                                stock_quote_data, future_earnings_data)
        earnings = Earnings(stock_valuation.current_earnings.earnings,
                            stock_valuation.current_earnings.calculated_price, stock_valuation.future_earnings.earnings,
                            stock_valuation.blended_earnings.earnings,
                            stock_valuation.max_earnings.earnings, stock_valuation.future_earnings.calculated_price,
                            stock_valuation.blended_earnings.calculated_price,
                            stock_valuation.max_earnings.calculated_price,
                            stock_data.treasury_yield, stock_valuation.dividend, stock_quote_data.open, datetime.now())
        db.session.add(earnings)
        db.session.query()
        db.session.commit()


def value_calculation(market_open, calculated_price):
    if market_open > calculated_price:
        valued_string = "OVERVALUED"
        valued_diff = (market_open - calculated_price) / calculated_price * 100
    else:
        valued_string = "UNDERVALUED"
        valued_diff = (calculated_price - market_open) / calculated_price * 100
    return {"valued": valued_string, "diff": valued_diff}


def cache_calculated_stock_data():
    with app.app_context():
        app.cache[SP_QUOTE_CALCULATED] = calculate_fair_market_value(app)


scheduler.add_job(id=STOCK_QUOTE_INTERVAL_TASK_ID, func=cache_quote, trigger='interval', seconds=60)
scheduler.add_job(id=MARKET_DATA_INTERVAL_TASK_ID, func=cache_market_values, trigger='interval', seconds=3000)
scheduler.add_job(id=FUTURE_VALUE_INTERVAL_TASK_ID, func=download_future_earnings, trigger='interval', seconds=60)
scheduler.add_job(id=VALUATION_INTERVAL_TASK_ID, func=cache_calculated_stock_data, trigger='interval', seconds=60)
scheduler.add_job(id=SAVE_FAIR_MARKET_DATA_TASK_ID, func=save_fair_market_value, trigger='interval', hours=1)


def initialize_shiller_data():
    shiller_data_service = ShillerDataService()
    use_existing = shiller_data_service.download_shiller_data()

    if not use_existing:
        # TODO use some flag to determine which regression model to use
        regression_data = shiller_data_service.get_ml_regression_data()
        # regression_data = shiller_data_service.get_fitted_regression_data()

        with app.app_context():
            logger = logging.getLogger(__name__)

            query = db.session.query(Coefficients)
            query = query.filter(
                and_(
                    Coefficients.treasury == regression_data['coefficients'].treasury,
                    Coefficients.dividend == regression_data['coefficients'].dividend,
                    Coefficients.earnings == regression_data['coefficients'].earnings
                )
            )
            query = query.with_entities(func.count())
            query_str = str(query)
            logger.info(f"Executing query: {query_str}")
            coefficient_count = query.scalar()
            if coefficient_count == 0:
                regression_values = Coefficients("S&P 500", regression_data['coefficients'].intercept,
                                             regression_data['coefficients'].treasury,
                                             regression_data['coefficients'].earnings,
                                             regression_data['coefficients'].dividend,
                                             regression_data['coefficients'].create_date)
                db.session.add(regression_values)
                db.session.commit()
    else:
        print('Using existing model')
        file = open('ml_model_regression.pkl', 'rb')
        coefficient_data = pickle.load(file)
        historical_data = pickle.load(file)
        return {'coefficients': coefficient_data, 'historicaldata': historical_data}
    return regression_data


with app.app_context():
    app.cache[SP_500] = initialize_shiller_data()
    app.cache[SP_QUOTE] = stock_quote_service.download_quote('^GSPC', '1d', '1m')
    app.cache[MARKETDATA] = market_value_service.download_market_values()
    app.cache[FUTURE_EARNINGS] = market_value_service.download_future_earnings()
    app.cache[SP_QUOTE_CALCULATED] = calculate_fair_market_value

# http://127.0.0.1:5000/sp-data
app.add_url_rule('/sp-data', view_func=StockDataView.as_view('stock_data'))


@app.route('/valuation-data/<symbol>')
@cross_origin()
def get_valuation_data(symbol=None):
    dictionary = collections.OrderedDict()
    dictionary['stock_valuation'] = calculate_fair_market_value()
    dictionary['market_data'] = app.cache.get(MARKETDATA)
    dictionary['equation_coefficients'] = app.cache.get(SP_500).get('coefficients')
    dictionary['timestamp'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    return json.dumps(dictionary, indent=4)


@app.route('/quote/<symbol>')
@cross_origin()
def get_stock_quote(symbol=None):
    dictionary = collections.OrderedDict()
    if symbol == 'GSPC':
        dictionary['market_quote'] = app.cache.get(SP_QUOTE)
    else:
        dictionary['market_quote'] = stock_quote_service.download_quote(symbol, '1d', '1m')
    return json.dumps(dictionary, indent=4)


@app.route('/historical-data/<symbol>')
@cross_origin()
def get_historical_data(symbol=None):
    dictionary = collections.OrderedDict()
    if symbol == GSPC:
        # convert GSPC to a variable

        dictionary['price_fairvalue'] = app.cache.get(SP_500).get('historicaldata')
    else:
        # TODO, should do something different here
        dictionary['price_fairvalue'] = stock_quote_service.download_quote(symbol, '1d', '1m')
    return json.dumps(dictionary, indent=4)


@app.route('/earnings/<symbol>')
@cross_origin()
def get_earnings(symbol=None):
    all_earnings = Earnings.query.all()
    results = earnings_schema.dumps(all_earnings)
    return results


# @cross_origin()
# @socketio.on('my event')
# def handle_my_custom_event(data):
#     emit('my response', data, broadcast=True)


# app.run(debug=False)
if __name__ == '__main__':
    app.run()
    # socketio.run(app)
