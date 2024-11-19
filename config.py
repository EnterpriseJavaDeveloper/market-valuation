# config.py
from dotenv import load_dotenv
import os

class Config:
    load_dotenv()
    db_conn = ("postgresql+psycopg2://{user}:{password}@{hostname}/{database}"
               .format(user=os.environ.get('user'), password=os.environ.get('password'), hostname=os.environ.get('host')
                       , database=os.environ.get('database')))

    SECRET_KEY = 'secret!'
    SQLALCHEMY_DATABASE_URI = db_conn
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT=300
    CORS_HEADERS = 'Content-Type'
    SCHEDULER_API_ENABLED = True
    SQLALCHEMY_ECHO = True
    # Add other configuration variables as needed