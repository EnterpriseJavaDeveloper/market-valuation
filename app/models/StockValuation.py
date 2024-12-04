import json
from json import JSONEncoder


class StockEarningsModel(dict):

    def __init__(self, earnings, earnings_type, calculated_price, valuation, valuation_pct):
        self.earnings = earnings
        self.earnings_type = earnings_type
        self.calculated_price = calculated_price
        self.valuation = valuation
        self.valuation_pct = valuation_pct
        dict.__init__(self, earnings=earnings, earnings_type=earnings_type, calculated_price=calculated_price, valuation=valuation)


class StockValuation(dict):

    def __init__(self, dividend, current_earnings: StockEarningsModel, future_earnings: StockEarningsModel, blended_earnings: StockEarningsModel, max_earnings: StockEarningsModel):
        self.dividend = dividend
        self.current_earnings = current_earnings
        self.future_earnings = future_earnings
        self.blended_earnings = blended_earnings
        self.max_earnings = max_earnings
        dict.__init__(self, dividend=dividend, current_earnings=current_earnings, future_earnings=future_earnings, blended_earnings=blended_earnings, max_earnings=max_earnings)


class StockValuationEncoder(JSONEncoder):

    def default(self, o):
        return o.__dict__;

