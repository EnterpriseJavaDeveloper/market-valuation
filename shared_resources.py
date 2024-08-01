import pickle
from flask import current_app as app
from FairMarketValueService import FairMarketValueService

fair_market_value_service = FairMarketValueService()


# def calculate_fair_market_value(app):
#     with app.app_context():
#         stock_data = app.cache.get('MARKETDATA')
#         coefficient_data = pickle.load(open('ml_model_regression.pkl', 'rb'))
#         stock_quote_data = app.cache.get('SP500QUOTE')
#         future_earnings_data = app.cache.get('FUTUREEARNINGS')
#         stock_valuation = fair_market_value_service.calculate_fair_market_value(stock_data, coefficient_data, stock_quote_data, future_earnings_data)
#     return stock_valuation