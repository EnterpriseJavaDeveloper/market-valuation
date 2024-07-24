from marshmallow import Schema, fields, post_load
from model.Earnings import Earnings


class EarningsSchema(Schema):
    id = fields.Integer()
    calculated_earnings = fields.Float()
    calculated_price = fields.Float()
    future_earnings = fields.Float()
    blended_earnings = fields.Float()
    max_earnings = fields.Float()
    future_price = fields.Float()
    blended_price = fields.Float()
    max_price = fields.Float()
    treasury_yield = fields.Float()
    dividend = fields.Float()
    current_price = fields.Float()
    event_time = fields.DateTime()

    @post_load
    def make_earnings(self, data, **kwargs):
        return Earnings(**data)
