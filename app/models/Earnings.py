from app.shared.database import db


class Earnings(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    calculated_earnings = db.Column(db.Float)
    calculated_price = db.Column(db.Float)
    future_earnings = db.Column(db.Float)
    blended_earnings = db.Column(db.Float)
    max_earnings = db.Column(db.Float)
    future_price = db.Column(db.Float)
    blended_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    treasury_yield = db.Column(db.Float)
    dividend = db.Column(db.Float)
    current_price = db.Column(db.Float)
    event_time = db.Column(db.DateTime)

    def __init__(self, calculated_earnings, calculated_price, future_earnings, blended_earnings, max_earnings,
                 future_price, blended_price, max_price, treasury_yield, dividend, current_price, event_time):
        self.calculated_earnings = calculated_earnings
        self.calculated_price = calculated_price
        self.future_earnings = future_earnings
        self.blended_earnings = blended_earnings
        self.max_earnings = max_earnings
        self.future_price = future_price
        self.blended_price = blended_price
        self.max_price = max_price
        self.treasury_yield = treasury_yield
        self.dividend = dividend
        self.current_price = current_price
        self.event_time = event_time
