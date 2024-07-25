import logging
import pickle
from datetime import datetime, timedelta

from database import db
from model.Coefficients import Coefficients
from model.Earnings import Earnings

logger = logging.getLogger()

from model.MarketData import MarketData
from model.StockQuote import StockQuote
from StockValuation import StockValuation, StockEarningsModel
from flask import current_app, app


class FairMarketValueService:

    @classmethod
    def calculate_fair_market_value(cls, stock_data: MarketData, regression_data: Coefficients,
                                    stock_quote_data: StockQuote, future_earnings_data):
        future_earnings = future_earnings_data['latest']
        max_future_earnings = future_earnings_data['max']
        dividend = stock_quote_data.open * stock_data.div_yield / 100
        earnings = stock_quote_data.open / stock_data.pe_ratio
        blended_earnings = (future_earnings + earnings) / 2
        current_app.logger.info(f'Current PE: {stock_data.pe_ratio}\tCurrent Price: {stock_quote_data.open}')
        current_app.logger.info(
            f'Calculated earnings (from PE): {earnings}\t'
            f'Future Earnings: {future_earnings}\t'
            f'Blended Earnings: {blended_earnings}\t'
            f'Max Earnings: {max_future_earnings}')
        calculated_price = regression_data.intercept + (regression_data.treasury * stock_data.treasury_yield) \
                           + (regression_data.dividend * dividend) + (regression_data.earnings * earnings)
        future_calculated_price = regression_data.intercept + (
                regression_data.treasury * stock_data.treasury_yield) \
                                  + (regression_data.dividend * dividend) + (
                                          regression_data.earnings * future_earnings)
        blended_calculated_price = regression_data.intercept + (
                regression_data.treasury * stock_data.treasury_yield) \
                                   + (regression_data.dividend * dividend) + (
                                           regression_data.earnings * blended_earnings)
        max_calculated_price = regression_data.intercept + (regression_data.treasury * stock_data.treasury_yield) \
                               + (regression_data.dividend * dividend) + (
                                       regression_data.earnings * max_future_earnings)
        valued = cls.value_calculation(stock_quote_data.open, calculated_price)
        current_earnings_model = StockEarningsModel(earnings, "Trailing earnings", calculated_price, valued["valued"],
                                                    valued["diff"])
        current_app.logger.info(
            f'Using calculated_price {calculated_price}: Market is {valued["valued"]} by: {valued["diff"]}%')
        valued = cls.value_calculation(stock_quote_data.open, future_calculated_price)
        future_earnings_model = StockEarningsModel(future_earnings, "Forward 12 month earnings",
                                                   future_calculated_price, valued["valued"], valued["diff"])
        current_app.logger.info(
            f'Using future_calculated_price {future_calculated_price}: Market is {valued["valued"]} by: {valued["diff"]}%')
        valued = cls.value_calculation(stock_quote_data.open, blended_calculated_price)
        blended_earnings_model = StockEarningsModel(blended_earnings, "Blending forward and trailing earnings",
                                                    blended_calculated_price, valued["valued"], valued["diff"])
        current_app.logger.info(
            f'Using blended_calculated_price {blended_calculated_price}: Market is {valued["valued"]} by: {valued["diff"]}%')
        valued = cls.value_calculation(stock_quote_data.open, max_calculated_price)
        max_earnings_model = StockEarningsModel(max_future_earnings, "Max forward earnings", max_calculated_price,
                                                valued["valued"], valued["diff"])
        current_app.logger.info(
            f'Using max_calculated_price {max_calculated_price}: Market is {valued["valued"]} by: {valued["diff"]}%')

        return StockValuation(dividend, current_earnings_model, future_earnings_model, blended_earnings_model,
                              max_earnings_model)

    @classmethod
    def value_calculation(cls, market_open, calculated_price):
        if market_open > calculated_price:
            valued_string = "OVERVALUED"
            valued_diff = (market_open - calculated_price) / calculated_price * 100
        else:
            valued_string = "UNDERVALUED"
            valued_diff = (calculated_price - market_open) / calculated_price * 100
        return {"valued": valued_string, "diff": valued_diff}

    @classmethod
    def save_fair_market_value(cls):
        with current_app.app_context():
            today = datetime.now().date()
            existing_earnings = Earnings.query.filter(Earnings.event_time > today - timedelta(days=1)).first()

            if existing_earnings:
                current_app.logger.info("Earnings have already been saved for today.")
                return
            stock_data = current_app.cache.get('MARKETDATA')
            coefficient_data = pickle.load(open('ml_model_regression.pkl', 'rb'))  # Adjust path as necessary
            stock_quote_data = current_app.cache.get('SP500QUOTE')
            future_earnings_data = current_app.cache.get('FUTUREEARNINGS')
            stock_valuation = cls.calculate_fair_market_value(stock_data, coefficient_data,
                                                                                 stock_quote_data, future_earnings_data)
            earnings = Earnings(stock_valuation.current_earnings.earnings,
                                stock_valuation.current_earnings.calculated_price,
                                stock_valuation.future_earnings.earnings,
                                stock_valuation.blended_earnings.earnings,
                                stock_valuation.max_earnings.earnings, stock_valuation.future_earnings.calculated_price,
                                stock_valuation.blended_earnings.calculated_price,
                                stock_valuation.max_earnings.calculated_price,
                                stock_data.treasury_yield, stock_valuation.dividend, stock_quote_data.open,
                                datetime.now())
            db.session.add(earnings)
            db.session.commit()
