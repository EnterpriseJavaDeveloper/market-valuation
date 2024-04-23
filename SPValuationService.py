import collections
import json
import multiprocessing
import pickle
import logging
from datetime import datetime

import pg8000 as pg

from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
from flask.logging import default_handler

from sqlalchemy import create_engine, text, select, func, and_
from sqlalchemy.orm import Session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

from CoefficientData import CoefficientData
from FairMarketValueService import FairMarketValueService
# from flask_socketio import SocketIO, emit
from flask_cors import CORS, cross_origin

from MarketValueService import MarketValueService
from ShillerDataService import ShillerDataService
import collections

from StockQuoteService import StockQuoteService

collections.Iterable = collections.abc.Iterable

SP_500 = 'SP500'
FUTURE_EARNINGS = 'FUTUREEARNINGS'
MARKETDATA = 'MARKETDATA'
SP_QUOTE = 'SP500QUOTE'
SP_QUOTE_CALCULATED = 'SP500QUOTECALCULATED'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:clouds58@localhost/MarketValuationDB'
db = SQLAlchemy(app)
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
app.logger.setLevel(logging.INFO)
engine = create_engine("postgresql+psycopg2://postgres:clouds58@localhost/MarketValuationDB")
with engine.connect() as conn:
    result = conn.execution_options(stream_results=True).execute(text("select * from earnings"))
# socketio = SocketIO(app)
conn = pg.connect(
    host="localhost",
    database="MarketValuationDB",
    user="postgres",
    password="clouds58")
STOCK_QUOTE_INTERVAL_TASK_ID = 'stock-quote-interval-task-id'
MARKET_DATA_INTERVAL_TASK_ID = 'market-data-interval-task-id'
VALUATION_INTERVAL_TASK_ID = 'valuation-interval-task-id'
FUTURE_VALUE_INTERVAL_TASK_ID = 'future-value-interval-task-id'
SAVE_FAIR_MARKET_DATA_TASK_ID = 'save-fair-market-data-task-id'
market_value_service = MarketValueService()
fair_market_value_service = FairMarketValueService()
stock_quote_service = StockQuoteService()


class Earnings(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    calculated_earnings = db.Column(db.Float)
    calculated_price = db.Column(db.Float)
    future_earnings = db.Column(db.Float)
    blended_earnings = db.Column(db.Float)
    max_earnings = db.Column(db.Float)
    future_price = db.Column(db.Float)
    blended_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    treasury_yield = db.Column(db.Float)
    dividend = db.Column(db.Float)
    current_price = db.Column(db.Float)
    event_time = db.Column(db.DateTime)

    def __init__(self, calculated_earnings, calculated_price, future_earnings, blended_earnings, max_earnings,
                 future_price, blended_price, max_price, treasury_yield, dividend, current_price, event_time):
        self.calculated_earnings = calculated_earnings
        self.calculated_price = calculated_price
        self.future_earnings = future_earnings
        self.blended_earnings = blended_earnings
        self.max_earnings = max_earnings
        self.future_price = future_price
        self.blended_price = blended_price
        self.max_price = max_price
        self.treasury_yield = treasury_yield
        self.dividend = dividend
        self.current_price = current_price
        self.event_time = event_time


class EarningsSchema(ma.Schema):
    class Meta:
        fields = ('id', 'calculated_earnings', 'calculated_price', 'future_earnings', 'blended_earnings', 'max_earnings',
                  'future_price', 'blended_price', 'max_price', 'treasury_yield', 'dividend', 'current_price', 'event_time')


earnings_schema = EarningsSchema(many=True)


def cache_quote():
    app.cache[SP_QUOTE] = stock_quote_service.download_quote('^GSPC', '1d', '1m')


def download_future_earnings():
    app.cache[FUTURE_EARNINGS] = market_value_service.download_future_earnings()


def cache_market_values():
    app.cache[MARKETDATA] = market_value_service.download_market_values()


def calculate_fair_market_value():
    stock_data = app.cache.get(MARKETDATA)
    # regression_data = app.cache.get('SP500')
    regression_data = pickle.load(open('ml_model.pkl', 'rb'))
    stock_quote_data = app.cache.get(SP_QUOTE)
    future_earnings_data = app.cache.get(FUTURE_EARNINGS)

    with app.app_context():
        stock_valuation = fair_market_value_service.calculate_fair_market_value(stock_data, regression_data, stock_quote_data, future_earnings_data)
    return stock_valuation


def save_fair_market_value():
    stock_data = app.cache.get(MARKETDATA)
    # regression_data = app.cache.get('SP500')
    regression_data = pickle.load(open('ml_model.pkl', 'rb'))  # TODO get regression data from database
    stock_quote_data = app.cache.get(SP_QUOTE)
    future_earnings_data = app.cache.get(FUTURE_EARNINGS)
    with app.app_context():
        stock_valuation = fair_market_value_service.calculate_fair_market_value(stock_data, regression_data, stock_quote_data, future_earnings_data)
        earnings = Earnings(stock_valuation.current_earnings.earnings, stock_valuation.current_earnings.calculated_price, stock_valuation.future_earnings.earnings, stock_valuation.blended_earnings.earnings,
                        stock_valuation.max_earnings.earnings, stock_valuation.future_earnings.calculated_price, stock_valuation.blended_earnings.calculated_price, stock_valuation.max_earnings.calculated_price,
                        stock_data.treasury_yield, stock_valuation.dividend, stock_quote_data.open, datetime.now())
        db.session.add(earnings)
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
        app.cache[SP_QUOTE_CALCULATED] = calculate_fair_market_value


scheduler.add_job(id=STOCK_QUOTE_INTERVAL_TASK_ID, func=cache_quote, trigger='interval', seconds=60)
scheduler.add_job(id=MARKET_DATA_INTERVAL_TASK_ID, func=cache_market_values, trigger='interval', seconds=3000)
scheduler.add_job(id=VALUATION_INTERVAL_TASK_ID, func=calculate_fair_market_value, trigger='interval', seconds=60)
scheduler.add_job(id=FUTURE_VALUE_INTERVAL_TASK_ID, func=download_future_earnings, trigger='interval', seconds=60)
scheduler.add_job(id=SAVE_FAIR_MARKET_DATA_TASK_ID, func=save_fair_market_value, trigger='interval', hours=1)


def initialize_shiller_data():
    shiller_data_service = ShillerDataService()
    shiller_data_service.download_shiller_data()
    regression_data = shiller_data_service.get_ml_regression_data()
    # regression_data = shiller_data_service.get_fitted_regression_data()
    session = Session(engine)
    query = session.query(CoefficientData)
    query = query.filter(
        and_(
            CoefficientData.treasury_coef == regression_data['coefficients'].treasury_coef,
            CoefficientData.dividend_coef == regression_data['coefficients'].dividend_coef,
            CoefficientData.earnings_coef == regression_data['coefficients'].earnings_coef
        )
    )
    query = query.with_entities(func.count())
    coefficient_count = query.scalar()
    if coefficient_count == 0:
        regression_values = CoefficientData("S&P 500", regression_data['coefficients'].intercept, regression_data['coefficients'].dividend_coef,
                                           regression_data['coefficients'].earnings_coef, regression_data['coefficients'].treasury_coef)
        session.add(regression_values)
        session.commit()
    return regression_data
    # return regression_data['coefficients']


with app.app_context():
    app.cache[SP_500] = initialize_shiller_data()
    app.cache[SP_QUOTE] = stock_quote_service.download_quote('^GSPC', '1d', '1m')
    app.cache[MARKETDATA] = market_value_service.download_market_values()
    app.cache[FUTURE_EARNINGS] = market_value_service.download_future_earnings()
    app.cache[SP_QUOTE_CALCULATED] = calculate_fair_market_value


# http://127.0.0.1:5000/sp-data
@app.route('/sp-data')
@cross_origin()
def get_stock_data():
    dictionary = collections.OrderedDict()
    dictionary['stock_valuation'] = calculate_fair_market_value()
    dictionary['market_data'] = app.cache.get(MARKETDATA)
    dictionary['equation_coefficients'] = app.cache.get(SP_500).get('coefficients')
    dictionary['timestamp'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    return json.dumps(dictionary, indent=4)


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
    if symbol == 'GSPC':
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
