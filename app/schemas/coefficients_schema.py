from marshmallow import Schema, fields, post_load

from app.models.Coefficients import Coefficients


class CoefficientsSchema(Schema):
    # class Meta:
    #     fields = ('id', 'intercept', 'treasury', 'earnings', 'dividend', 'name', 'create_date')

    # id = fields.Integer()
    intercept = fields.Float()
    treasury = fields.Float()
    earnings = fields.Float()
    dividend = fields.Float()
    name = fields.String()
    create_date = fields.DateTime()

    @post_load
    def make_coefficient(self, data, **kwargs):
        return Coefficients(**data)