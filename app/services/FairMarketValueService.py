import logging
import pickle
from datetime import datetime, timedelta

from app.services.MarketValueService import MarketValueService
from app.services.StockQuoteService import StockQuoteService
from database import db
from model.Earnings import Earnings
from StockValuation import StockValuation, StockEarningsModel
from flask import current_app

logger = logging.getLogger()


class FairMarketValueService:

    @classmethod
    def calculate_fair_market_value(cls):
        stock_data = MarketValueService.download_market_values()
        regression_data = pickle.load(open('../ml_model_regression.pkl', 'rb'))
        stock_quote_data = StockQuoteService.download_quote('^GSPC', '1d', '1m')
        future_earnings_data = MarketValueService.download_future_earnings()
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
        # intercept = regression_data.get('intercept')
        # treasury_coefficient = regression_data.get('treasury')
        # dividend_coefficient = regression_data.get('dividend')
        # earnings_coefficient = regression_data.get('earnings')

        intercept = regression_data.intercept
        treasury_coefficient = regression_data.treasury
        dividend_coefficient = regression_data.dividend
        earnings_coefficient = regression_data.earnings

        calculated_price = intercept + (treasury_coefficient * stock_data.treasury_yield) \
                           + (dividend_coefficient * dividend) + (earnings_coefficient * earnings)
        future_calculated_price = intercept + (
                treasury_coefficient * stock_data.treasury_yield) \
                                  + (dividend_coefficient * dividend) + (
                                          earnings_coefficient * future_earnings)
        blended_calculated_price = intercept + (
                treasury_coefficient * stock_data.treasury_yield) \
                                   + (dividend_coefficient * dividend) + (
                                           earnings_coefficient * blended_earnings)
        max_calculated_price = intercept + (treasury_coefficient * stock_data.treasury_yield) \
                               + (dividend_coefficient * dividend) + (
                                       earnings_coefficient * max_future_earnings)
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
            db.session.begin()
            existing_earnings = Earnings.query.filter(Earnings.event_time > today - timedelta(days=1)).first()

            if existing_earnings:
                current_app.logger.info("Earnings have already been saved for today.")
                return
            stock_data = MarketValueService.download_market_values()
            stock_quote_data = StockQuoteService.download_quote('^GSPC', '1d', '1m')
            stock_valuation = cls.calculate_fair_market_value()
            earnings = Earnings(stock_valuation.current_earnings.earnings.item(),
                            stock_valuation.current_earnings.calculated_price.item(),
                            stock_valuation.future_earnings.earnings,
                            stock_valuation.blended_earnings.earnings.item(),
                            stock_valuation.max_earnings.earnings.item(), stock_valuation.future_earnings.calculated_price.item(),
                            stock_valuation.blended_earnings.calculated_price.item(),
                            stock_valuation.max_earnings.calculated_price.item(),
                            stock_data.treasury_yield, stock_valuation.dividend.item(), stock_quote_data.open.item(),
                            datetime.now())
            db.session.add(earnings)
            db.session.commit()
