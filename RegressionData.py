from simplestr import gen_str, gen_repr, gen_eq


@gen_str
@gen_repr
@gen_eq
class RegressionData(dict):

    def __init__(self, name, intercept, dividend_coef, earnings_coef, treasury_coef, price_fairvalue):
        self.name = name
        self.intercept = intercept
        self.dividend_coef = dividend_coef
        self.earnings_coef = earnings_coef
        self.treasury_coef = treasury_coef
        self.price_fairvalue = price_fairvalue
        dict.__init__(self, name=name, intercept=intercept, dividend_coef=dividend_coef, earnings_coef=earnings_coef, treasury_coef=treasury_coef, price_fairvalue=price_fairvalue.to_json(orient='table', index=False))
