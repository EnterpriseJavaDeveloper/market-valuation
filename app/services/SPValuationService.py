import json
from datetime import datetime
from flask import request
from flask_cors import cross_origin

import collections
from app.endpoints.AuthService import AuthService
from app.models.Earnings import Earnings
from app.schemas.earnings_schema import EarningsSchema
from app.services.FairMarketValueService import FairMarketValueService
from app.services.MarketValueService import MarketValueService
from app.services.ShillerDataService import ShillerDataService
from app.schemas.coefficients_schema import CoefficientsSchema
from caching import cache

# app = create_app()

# GSPC = 'GSPC'
# SP_500 = 'SP500'
# FUTURE_EARNINGS = 'FUTUREEARNINGS'
# MARKETDATA = 'MARKETDATA'
# SP_QUOTE = 'SP500QUOTE'
# SP_QUOTE_CALCULATED = 'SP500QUOTECALCULATED'
#
# coefficients_schema = CoefficientsSchema(many=False)
# earnings_schema = EarningsSchema(many=True)
#
# def cache_quote():
#     cache.set(SP_QUOTE, stock_quote_service.download_quote('^GSPC', '1d', '1m'))
#
# def download_future_earnings():
#     cache.set(FUTURE_EARNINGS, market_value_service.download_future_earnings())
#
# def cache_market_values():
#     cache.set(MARKETDATA, market_value_service.download_market_values())
#
# def cache_calculated_stock_data():
#     with app.app_context():
#         cache.set(SP_QUOTE_CALCULATED, FairMarketValueService.calculate_fair_market_value())
#
# def save_fair_market_value():
#     with app.app_context():
#         fair_market_value_service.save_fair_market_value()

# @app.route('/valuation-data/<symbol>')
# @cross_origin()
# def get_valuation_data(symbol=None):
#     dictionary = collections.OrderedDict()
#     dictionary['stock_valuation'] = FairMarketValueService.calculate_fair_market_value()
#     dictionary['market_data'] = MarketValueService.download_market_values()
#     coefficients = coefficients_schema.dump(ShillerDataService.initialize_shiller_data().get('coefficients'))
#     dictionary['equation_coefficients'] = coefficients
#     dictionary['timestamp'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
#     return json.dumps(dictionary, indent=4)
#
# @app.route('/quote/<symbol>')
# @cross_origin()
# def get_stock_quote(symbol=None):
#     dictionary = collections.OrderedDict()
#     if symbol == 'GSPC':
#         dictionary['market_quote'] = stock_quote_service.download_quote('^GSPC', '1d', '1m')
#     else:
#         dictionary['market_quote'] = stock_quote_service.download_quote(symbol, '1d', '1m')
#     return json.dumps(dictionary, indent=4)
#
# @app.route('/historical-data/<symbol>')
# @cross_origin()
# def get_historical_data(symbol=None):
#     dictionary = collections.OrderedDict()
#     if symbol == GSPC:
#         historical_data = ShillerDataService.initialize_shiller_data().get('historicaldata')
#         dictionary['price_fairvalue'] = historical_data
#         last_date_str = ShillerDataService.initialize_shiller_data().get('lastdate')
#         if last_date_str:
#             last_date = datetime.strptime(last_date_str, '%Y/%m/%d')
#             earnings = Earnings.query.filter(Earnings.event_time > last_date).all()
#             earnings = [e for e in earnings if e.event_time.month > last_date.month]
#             from itertools import groupby
#             from operator import attrgetter
#             earnings.sort(key=attrgetter('event_time'))
#             grouped_earnings = []
#             for key, group in groupby(earnings, key=lambda x: (x.event_time.year, x.event_time.month)):
#                 last_row = list(group)[-1]
#                 grouped_earnings.append(last_row)
#             for earning in grouped_earnings:
#                 earning.event_time = earning.event_time.replace(day=1).strftime('%Y/%m/%d')
#             earnings_schema = EarningsSchema(many=True)
#             earnings_dict = earnings_schema.dump(grouped_earnings)
#             dictionary['calculated_price_fairvalue'] = earnings_dict
#     else:
#         dictionary['price_fairvalue'] = stock_quote_service.download_quote(symbol, '1d', '1m')
#     return json.dumps(dictionary, indent=4)
#
# @app.route('/earnings/<symbol>')
# @cross_origin()
# def get_earnings(symbol=None):
#     all_earnings = Earnings.query.all()
#     results = earnings_schema.dumps(all_earnings)
#     return results
#
# @app.route('/login', methods=['POST'])
# @cross_origin()
# def login():
#     data = request.get_json()
#     return AuthService.login(data)