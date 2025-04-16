from datetime import datetime


class MarketData(dict):
    pe_ratio = 0
    div_yield = 0
    treasury_yield = 0
    dividend = 0
    dividend_growth = 0
    earnings = 0
    dividend_timestamp = None
    dividend_growth_timestamp = None

    def __init__(self, pe_ratio, div_yield, treasury_yield, dividend, dividend_timestamp, dividend_growth, dividend_growth_timestamp):
        self.pe_ratio = pe_ratio
        self.div_yield = div_yield
        self.treasury_yield = treasury_yield
        self.dividend = dividend
        self.dividend_timestamp = dividend_timestamp
        self.dividend_growth = dividend_growth
        self.dividend_growth_timestamp = dividend_growth_timestamp
        dict.__init__(self, pe_ratio=pe_ratio, div_yield=div_yield, treasury_yield=treasury_yield, dividend=dividend,
                      dividend_timestamp=dividend_timestamp, dividend_growth=dividend_growth, dividend_growth_timestamp=dividend_growth_timestamp)

    def to_dict(self):
        return {
            "pe_ratio": self.pe_ratio,
            "div_yield": self.div_yield,
            "treasury_yield": self.treasury_yield,
            "dividend": self.dividend,
            "dividend_timestamp": self.dividend_timestamp.isoformat() if isinstance(self.dividend_timestamp, datetime) else None,
            "dividend_growth": self.dividend_growth,
            "dividend_growth_timestamp": self.dividend_growth_timestamp.isoformat() if isinstance(self.dividend_growth_timestamp, datetime) else None,
        }

    def to_json(self):
        import json
        return json.dumps(self.to_dict(), indent=4)