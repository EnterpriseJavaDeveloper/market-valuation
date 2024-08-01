from flask.views import MethodView
from FairMarketValueService import FairMarketValueService
from caching import cache
from schema.coefficients_schema import CoefficientsSchema
from flask_cors import cross_origin
import collections
import json
from datetime import datetime

coefficients_schema = CoefficientsSchema(many=False)


class StockDataView(MethodView):
    @cross_origin()
    def get(self):
        dictionary = collections.OrderedDict()
        dictionary['stock_valuation'] = FairMarketValueService.calculate_fair_market_value()
        dictionary['market_data'] = cache.get('MARKETDATA')
        json_output = coefficients_schema.dump(cache.get('SP500').get('coefficients'))
        dictionary['equation_coefficients'] = json_output
        dictionary['timestamp'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        return json.dumps(dictionary, indent=4)


