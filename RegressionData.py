from simplestr import gen_str, gen_repr, gen_eq
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from Base import Base


@gen_str
@gen_repr
@gen_eq
class RegressionData(dict, Base):

    __tablename__ = "coefficients"

    id: Mapped[int] = mapped_column(primary_key=True)
    intercept: Mapped[float] = mapped_column(Float)
    treasury_coef: Mapped[float] = mapped_column('treasury', Float)
    earnings_coef: Mapped[float] = mapped_column('earnings', Float)
    dividend_coef: Mapped[float] = mapped_column('dividend', Float)
    name: Mapped[str] = mapped_column(String(30))

    def __init__(self, name, intercept, dividend_coef, earnings_coef, treasury_coef, price_fairvalue=None):
        self.name = name
        self.intercept = intercept
        self.dividend_coef = dividend_coef
        self.earnings_coef = earnings_coef
        self.treasury_coef = treasury_coef
        self.price_fairvalue = price_fairvalue
        if price_fairvalue is not None:
            dict.__init__(self, name=name, intercept=intercept, dividend_coef=dividend_coef, earnings_coef=earnings_coef, treasury_coef=treasury_coef, price_fairvalue=price_fairvalue.to_json(orient='table', index=False))

