import collections
import json
import multiprocessing
import pickle
import logging
import pg8000 as pg

from flask import Flask, render_template
from flask_apscheduler import APScheduler
from flask.logging import default_handler


from FairMarketValueService import FairMarketValueService
# from flask_socketio import SocketIO, emit
# from flask_cors import CORS, cross_origin

from MarketValueService import MarketValueService
from ShillerDataService import ShillerDataService

SP_500 = 'SP500'
FUTURE_EARNINGS = 'FUTUREEARNINGS'
MARKETDATA = 'MARKETDATA'
SP_QUOTE = 'SP500QUOTE'
SP_QUOTE_CALCULATED = 'SP500QUOTECALCULATED'

app = Flask(__name__, template_folder='templates/')
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


def cache_quote():
    app.cache[SP_QUOTE] = market_value_service.download_quote()


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
    conn.run("START TRANSACTION")
    conn.run("INSERT INTO earnings (calculated_earnings, calculated_price, future_earnings, blended_earnings,"
             " max_earnings, future_price, blended_price, max_price, treasury_yield, dividend, current_price) "
             "values (:calculated_earnings, :calculated_price, :future_earnings, :blended_earnings, :max_earnings, "
             ":future_price, :blended_price, :max_price, :treasury_yield, :dividend, :current_price)",
             calculated_earnings=stock_valuation.current_earnings.earnings, calculated_price=stock_valuation.current_earnings.calculated_price, future_earnings=stock_valuation.future_earnings.earnings,
             blended_earnings=stock_valuation.blended_earnings.earnings, max_earnings=stock_valuation.max_earnings.earnings, future_price=stock_valuation.future_earnings.calculated_price,
             blended_price=stock_valuation.blended_earnings.calculated_price, max_price=stock_valuation.max_earnings.calculated_price,
             treasury_yield=stock_data.treasury_yield, dividend=stock_valuation.dividend, current_price=stock_quote_data.open)
    conn.commit()


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
    regression_data = shiller_data_service.get_regression_data()

    coefficient_count = conn.run("select count(*) from coefficients c where c.treasury=:treasury"
                                 " and  c.dividend=:dividend and c.earnings=earnings",
                                 treasury=regression_data.treasury_coef, dividend=regression_data.dividend_coef,
                                 earnings=regression_data.earnings_coef)
    if coefficient_count[0] == [0]:
        conn.run("START TRANSACTION")
        conn.run("Insert into coefficients (intercept, dividend, earnings, treasury) "
                 "values (:intercept, :dividend, :earnings, :treasury)",
                 intercept=regression_data.intercept, dividend=regression_data.dividend_coef,
                 earnings=regression_data.earnings_coef, treasury=regression_data.treasury_coef)
        conn.commit()
    return regression_data


with app.app_context():
    app.cache[SP_500] = initialize_shiller_data()
    app.cache[SP_QUOTE] = market_value_service.download_quote()
    app.cache[MARKETDATA] = market_value_service.download_market_values()
    app.cache[FUTURE_EARNINGS] = market_value_service.download_future_earnings()
    app.cache[SP_QUOTE_CALCULATED] = calculate_fair_market_value


# http://127.0.0.1:5000/sp-data
@app.route('/sp-data')
def get_stock_data():
    dictionary = collections.OrderedDict()
    dictionary['stock_valuation'] = calculate_fair_market_value()
    dictionary['market_data'] = app.cache.get(MARKETDATA)
    dictionary['market_quote'] = app.cache.get(SP_QUOTE)
    dictionary['equation_coefficients'] = app.cache.get(SP_500)
    # stock_valuation = calculate_fair_market_value()
    # print(stock_valuation.calculated_price)
    return json.dumps(dictionary, indent=4)


# @cross_origin()
# @socketio.on('my event')
# def handle_my_custom_event(data):
#     emit('my response', data, broadcast=True)


# app.run(debug=False)
if __name__ == '__main__':
    app.run()
    # socketio.run(app)
