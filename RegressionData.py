import json

from simplestr import gen_str, gen_repr, gen_eq


@gen_str
@gen_repr
@gen_eq
class RegressionData(dict):

    def __init__(self, price_fairvalue):
        self.price_fairvalue = price_fairvalue
        history = price_fairvalue.to_json(orient='records')
        history = history.replace(' ', "_")
        historyObj = json.loads(history)
        dict.__init__(self, price_fairvalue=historyObj)

