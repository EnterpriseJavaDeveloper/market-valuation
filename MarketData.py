class MarketData(dict):
    pe_ratio = 0
    div_yield = 0
    treasury_yield = 0
    dividend = 0
    earnings = 0

    def __init__(self, pe_ratio, div_yield, treasury_yield):
        self.pe_ratio = pe_ratio
        self.div_yield = div_yield
        self.treasury_yield = treasury_yield
        dict.__init__(self, pe_ratio=pe_ratio, div_yield=div_yield, treasury_yield=treasury_yield)
