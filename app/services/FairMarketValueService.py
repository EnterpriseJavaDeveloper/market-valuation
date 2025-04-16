import logging
import pickle
from datetime import datetime, timedelta, date

from dateutil.relativedelta import relativedelta

from app.services.MarketValueService import MarketValueService
from app.services.StockQuoteService import StockQuoteService
from app.shared.database import db
from app.models.Earnings import Earnings
from app.models.StockValuation import StockValuation, StockEarningsModel
from flask import current_app

logger = logging.getLogger()


class FairMarketValueService:

    @classmethod
    def calculate_fair_market_value(cls):
        stock_data = MarketValueService.download_market_values()
        regression_data = pickle.load(open('../ml_model_regression.pkl', 'rb'))
        stock_quote_data = StockQuoteService.download_quote('^GSPC', '1d', '1m')
        earnings_data = MarketValueService.download_future_earnings()
        future_earnings = earnings_data['future']
        future_earnings_date = earnings_data['future_date']
        monthly_dividend_growth_rate = stock_data.dividend_growth / 12
        current_date = date.today()
        months_difference = relativedelta(current_date, stock_data.dividend_timestamp).months + \
                            (relativedelta(current_date, stock_data.dividend_timestamp).years * 12)

        print(f'Future earnings date: {future_earnings_date}, dividends date: {stock_data.dividend_timestamp}, monthly dividend growth rate: {monthly_dividend_growth_rate}')
        # Calculate the difference in months
        future_dividends_months_difference = relativedelta(future_earnings_date, stock_data.dividend_timestamp).months + \
                            (relativedelta(future_earnings_date, stock_data.dividend_timestamp).years * 12)
        print(f"Months difference: {future_dividends_months_difference}")
        max_future_earnings = earnings_data['max']
        max_future_earnings_date = earnings_data['max_date']
        max_future_dividends_months_difference = relativedelta(max_future_earnings_date, stock_data.dividend_timestamp).months + \
                            (relativedelta(max_future_earnings_date, stock_data.dividend_timestamp).years * 12)
        dividend = stock_data.dividend
        current_dividend = dividend * ((1 + (monthly_dividend_growth_rate / 100)) ** months_difference)
        # Calculate the compounded dividend
        future_dividend = stock_data.dividend * ((1 + (monthly_dividend_growth_rate / 100)) ** future_dividends_months_difference)
        max_dividend = stock_data.dividend * ((1 + (monthly_dividend_growth_rate / 100)) ** max_future_dividends_months_difference)
        print(f"Future Dividend after {future_dividends_months_difference} months: {future_dividend}")
        print(f"Max Dividend after {max_future_dividends_months_difference} months: {max_dividend}")
        trailing_earnings = earnings_data['trailing']
        blended_earnings = earnings_data['blended']
        blended_earnings_date = earnings_data['blended_date']
        blended_dividends_months_difference = relativedelta(blended_earnings_date, stock_data.dividend_timestamp).months + \
                                              (relativedelta(blended_earnings_date, stock_data.dividend_timestamp).years * 12)
        blended_dividend = stock_data.dividend * ((1 + (monthly_dividend_growth_rate / 100)) ** blended_dividends_months_difference)
        current_app.logger.info(f'Current PE: {stock_data.pe_ratio}\tCurrent Price: {stock_quote_data.open}')
        current_app.logger.info(
            f'Trailing earnings: {trailing_earnings}\t'
            f'Future Earnings: {future_earnings}\t'
            f'Blended Earnings: {blended_earnings}\t'
            f'Max Earnings: {max_future_earnings}')

        intercept = regression_data.intercept
        treasury_coefficient = regression_data.treasury
        dividend_coefficient = regression_data.dividend
        earnings_coefficient = regression_data.earnings

        trailing_calculated_price = intercept + (treasury_coefficient * stock_data.treasury_yield) \
                           + (dividend_coefficient * current_dividend) + (earnings_coefficient * trailing_earnings)
        future_calculated_price = intercept + (
                treasury_coefficient * stock_data.treasury_yield) \
                                  + (dividend_coefficient * future_dividend) + (
                                          earnings_coefficient * future_earnings)
        blended_calculated_price = intercept + (
                treasury_coefficient * stock_data.treasury_yield) \
                                   + (dividend_coefficient * blended_dividend) + (
                                           earnings_coefficient * blended_earnings)
        max_calculated_price = intercept + (treasury_coefficient * stock_data.treasury_yield) \
                               + (dividend_coefficient * max_dividend) + (
                                       earnings_coefficient * max_future_earnings)
        valued = cls.value_calculation(stock_quote_data.open, trailing_calculated_price)
        trailing_earnings_model = StockEarningsModel(trailing_earnings, "Trailing earnings", trailing_calculated_price, valued["valued"],
                                                    valued["diff"])
        current_app.logger.info(
            f'Using trailing_price {trailing_calculated_price}: Market is {valued["valued"]} by: {valued["diff"]}%')
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

        return StockValuation(dividend, trailing_earnings_model, future_earnings_model, blended_earnings_model,
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
                            stock_data.treasury_yield, stock_valuation.dividend, stock_quote_data.open.item(),
                            datetime.now())
            db.session.add(earnings)
            db.session.commit()
