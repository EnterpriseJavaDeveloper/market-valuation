from dataclasses import dataclass
from database import db

@dataclass
class Users(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String)
    password = db.Column(db.String)
    email = db.Column(db.String)
    create_date = db.Column(db.DateTime)

    def __init__(self, username, password, email, create_date):
        self.username = username
        self.password = password
        self.email = email
        self.create_date = create_date