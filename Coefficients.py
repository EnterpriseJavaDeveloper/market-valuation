from dataclasses import dataclass

from database import db


@dataclass
class Coefficients(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    treasury = db.Column(db.Float)
    intercept = db.Column(db.Float)
    earnings = db.Column(db.Float)
    dividend = db.Column(db.Float)
    name = db.Column(db.String)
    create_date = db.Column(db.DateTime)

    def __init__(self, name, intercept, treasury, earnings, dividend, create_date):
        self.name = name
        self.intercept = intercept
        self.treasury = treasury
        self.earnings = earnings
        self.dividend = dividend
        self.create_date = create_date
