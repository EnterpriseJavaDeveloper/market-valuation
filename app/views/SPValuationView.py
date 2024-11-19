from flask import Blueprint, request, jsonify
from flask.views import MethodView
from flask_cors import cross_origin
import json
import collections
from datetime import datetime
from app.endpoints.AuthService import AuthService
from app.models.Earnings import Earnings
from app.schemas.earnings_schema import EarningsSchema
from app.services.FairMarketValueService import FairMarketValueService
from app.services.MarketValueService import MarketValueService
from app.services.ShillerDataService import ShillerDataService
from app.schemas.coefficients_schema import CoefficientsSchema
from app.services.StockQuoteService import StockQuoteService
from caching import cache

bp = Blueprint('sp_valuation_view', __name__)
coefficients_schema = CoefficientsSchema(many=False)
earnings_schema = EarningsSchema(many=True)

class SPValuationView(MethodView):
    @cross_origin()
    def get_valuation_data(self, symbol=None):
        dictionary = collections.OrderedDict()
        dictionary['stock_valuation'] = FairMarketValueService.calculate_fair_market_value()
        dictionary['market_data'] = MarketValueService.download_market_values()
        coefficients = coefficients_schema.dump(ShillerDataService.initialize_shiller_data().get('coefficients'))
        dictionary['equation_coefficients'] = coefficients
        dictionary['timestamp'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        return json.dumps(dictionary, indent=4)

    @cross_origin()
    def get_stock_quote(self, symbol=None):
        dictionary = collections.OrderedDict()
        if symbol == 'GSPC':
            dictionary['market_quote'] = StockQuoteService.download_quote('^GSPC', '1d', '1m')
        else:
            dictionary['market_quote'] = StockQuoteService.download_quote(symbol, '1d', '1m')
        return json.dumps(dictionary, indent=4)

    @cross_origin()
    def get_historical_data(self, symbol=None):
        dictionary = collections.OrderedDict()
        if symbol == 'GSPC':
            historical_data = ShillerDataService.initialize_shiller_data().get('historicaldata')
            dictionary['price_fairvalue'] = historical_data
            last_date_str = ShillerDataService.initialize_shiller_data().get('lastdate')
            if last_date_str:
                last_date = datetime.strptime(last_date_str, '%Y/%m/%d')
                earnings = Earnings.query.filter(Earnings.event_time > last_date).all()
                earnings = [e for e in earnings if e.event_time.month > last_date.month]
                from itertools import groupby
                from operator import attrgetter
                earnings.sort(key=attrgetter('event_time'))
                grouped_earnings = []
                for key, group in groupby(earnings, key=lambda x: (x.event_time.year, x.event_time.month)):
                    last_row = list(group)[-1]
                    grouped_earnings.append(last_row)
                for earning in grouped_earnings:
                    earning.event_time = earning.event_time.replace(day=1).strftime('%Y/%m/%d')
                earnings_schema = EarningsSchema(many=True)
                earnings_dict = earnings_schema.dump(grouped_earnings)
                dictionary['calculated_price_fairvalue'] = earnings_dict
        else:
            dictionary['price_fairvalue'] = StockQuoteService.download_quote(symbol, '1d', '1m')
        return json.dumps(dictionary, indent=4)

    @cross_origin()
    def get_earnings(self, symbol=None):
        all_earnings = Earnings.query.all()
        results = earnings_schema.dumps(all_earnings)
        return results

    @cross_origin()
    def login(self):
        data = request.get_json()
        return AuthService.login(data)

bp.add_url_rule('/valuation-data/<symbol>', view_func=SPValuationView.as_view('get_valuation_data'), methods=['GET'])
bp.add_url_rule('/quote/<symbol>', view_func=SPValuationView.as_view('get_stock_quote'), methods=['GET'])
bp.add_url_rule('/historical-data/<symbol>', view_func=SPValuationView.as_view('get_historical_data'), methods=['GET'])
bp.add_url_rule('/earnings/<symbol>', view_func=SPValuationView.as_view('get_earnings'), methods=['GET'])
bp.add_url_rule('/login', view_func=SPValuationView.as_view('login'), methods=['POST'])