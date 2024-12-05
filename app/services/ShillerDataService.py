import os
import time
import urllib
from datetime import datetime

import numpy as np
import pandas as pd
import pickle

from flask import current_app
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sqlalchemy import and_, func
import logging

from app.shared.caching import cache
from app.shared.database import db
from app.models.Coefficients import Coefficients
from app.models.RegressionData import RegressionData


class ShillerDataService:
    schiller_data_url = "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/ie_data.xls"
    # schiller_data_url = "http://www.econ.yale.edu//~shiller/data/ie_data.xls"
    file = "../shiller.xls"
    shiller_df = pd.DataFrame()
    incomplete_data = pd.DataFrame()
    last_date = ''

    @classmethod
    @cache.cached(timeout=86400, key_prefix='shiller_data')
    def initialize_shiller_data(cls):
        use_existing = cls.download_shiller_data()

        if not use_existing:
            regression_data = cls.get_ml_regression_data()
            # regression_data = cls.get_fitted_regression_data()

            treasury = float(regression_data['coefficients'].treasury)
            dividend = float(regression_data['coefficients'].dividend)
            earnings = float(regression_data['coefficients'].earnings)
            intercept = float(regression_data['coefficients'].intercept)

            with current_app.app_context():
                logger = logging.getLogger(__name__)

                query = db.session.query(Coefficients)
                query = query.filter(
                    and_(
                        Coefficients.treasury == treasury,
                        Coefficients.dividend == dividend,
                        Coefficients.earnings ==earnings
                    )
                )
                query = query.with_entities(func.count())
                query_str = str(query)
                logger.info(f"Executing query: {query_str}")
                coefficient_count = query.scalar()
                if coefficient_count == 0:
                    regression_values = Coefficients("S&P 500", intercept,
                                                     treasury,
                                                     earnings,
                                                     dividend,
                                                     regression_data['coefficients'].create_date)
                    db.session.add(regression_values)
                    db.session.commit()
        else:
            print('Using existing model')
            file = open('../ml_model_regression.pkl', 'rb')
            coefficient_data = pickle.load(file)
            historical_data = pickle.load(file)
            last_date = pickle.load(file)
            print (last_date)
            return {'coefficients': coefficient_data, 'historicaldata': historical_data, 'lastdate': last_date}
        return regression_data

    @classmethod
    def download_shiller_data(cls):
        use_existing = False
        if not os.path.exists(cls.file):
            print('Retrieving new shiller data file')
            urllib.request.urlretrieve(cls.schiller_data_url, cls.file)
        else:
            modified = os.path.getmtime(cls.file)
            dayssince = (time.time() - modified) / 3600 / 24
            if dayssince > 10:
                print('Retrieving new shiller data file')
                urllib.request.urlretrieve(cls.schiller_data_url, cls.file)
            else:
                print('Use existing stored model')
                use_existing = True

        if not use_existing:
            df = pd.read_excel(cls.file, sheet_name='Data', skiprows=range(0, 7), skipfooter=1, usecols='A:D,G:I,K')
            df.replace({'D',''}, np.nan, inplace=True)
            df.replace({'Dividend',''}, np.nan, inplace=True)
            df.replace({'Earnings', ''}, np.nan, inplace=True)
            df.replace({'E', ''}, np.nan, inplace=True)
            cls.incomplete_data = df[df[['Dividend', 'Earnings', 'D', 'E']].isna().any(axis=1)]
            df.dropna(subset=['Dividend', 'Earnings', 'D', 'E'], inplace=True)
            df['Date'] = df['Date'].astype(str).replace(r'\.', '/', regex=True).apply(lambda x: x + '0' if len(x) == 6 else x).apply(lambda x: x + '/01')
            last_date = df['Date'].iloc[-1]
            print(last_date)
            # drop all rows before Jan 1, 1960
            # i = 1068
            i = df.index[df['Date'] == '1900/01/01'].tolist()[0]
            # i = 4
            cls.shiller_df = df.drop(df.index[:i])
            cls.last_date = last_date
        return use_existing

    @classmethod
    def get_fitted_regression_data(cls):
        mlr = LinearRegression()
        mlr.fit(cls.shiller_df[['Dividend', 'Earnings', 'Rate GS10']], cls.shiller_df['Price'])
        cls.shiller_df['FairValue'] = cls.shiller_df.loc[:, 'Dividend'] * mlr.coef_[0] + \
            cls.shiller_df.loc[:, 'Earnings'] * mlr.coef_[1] + cls.shiller_df.loc[:, 'Rate GS10'] * mlr.coef_[2] + \
            mlr.intercept_
        treasury_coef = mlr.coef_[2]
        dividend_coef = mlr.coef_[0]
        earnings_coef = mlr.coef_[1]
        price_fairvalue = cls.shiller_df[['Date', 'Price', 'FairValue', 'Dividend', 'Earnings', 'P', 'D', 'E', 'Rate GS10']]
        price_fairvalue = price_fairvalue.rename(str.lower, axis='columns')
        price_fairvalue = price_fairvalue.rename(columns={'p': 'actualprice', 'd': 'actualdividend', 'e': 'actualearnings'})
        regression_data = RegressionData(price_fairvalue)
        coefficient_data = Coefficients('SP_500', mlr.intercept_, treasury_coef, earnings_coef, dividend_coef, datetime.now())
        file = open('ml_model_fitted.pkl', 'wb')
        pickle.dump(coefficient_data, file)
        pickle.dump(regression_data['price_fairvalue'], file)
        pickle.dump(cls.last_date, file)
        file.close()
        return {'coefficients': coefficient_data, 'historicaldata': regression_data['price_fairvalue'], 'lastdate': cls.last_date}

    @classmethod
    def get_ml_regression_data(cls):
        mlr = LinearRegression()
        x_training_data, x_test_data, y_training_data, y_test_data = train_test_split(cls.shiller_df[['Dividend', 'Earnings', 'Rate GS10']], cls.shiller_df['Price'], test_size=0.3)
        mlr.fit(x_training_data, y_training_data)
        predictions = mlr.predict(x_test_data)
        mean_absolute_error = metrics.mean_absolute_error(y_test_data, predictions)
        mean_squared_error = metrics.mean_squared_error(y_test_data, predictions)
        root_mean_squared_error = np.sqrt(mean_squared_error)
        score = mlr.score(x_training_data, y_training_data)
        cls.shiller_df['FairValue'] = cls.shiller_df.loc[:, 'Dividend'] * mlr.coef_[0] + \
            cls.shiller_df.loc[:, 'Earnings'] * mlr.coef_[1] + cls.shiller_df.loc[:, 'Rate GS10'] * mlr.coef_[2] + \
            mlr.intercept_
        treasury_coef = mlr.coef_[2]
        dividend_coef = mlr.coef_[0]
        earnings_coef = mlr.coef_[1]
        price_fairvalue = cls.shiller_df[['Date', 'Price', 'FairValue', 'Dividend', 'Earnings', 'P', 'D', 'E', 'Rate GS10']]
        price_fairvalue = price_fairvalue.rename(str.lower, axis='columns')
        price_fairvalue = price_fairvalue.rename(columns={'p': 'actualprice', 'd': 'actualdividend', 'e': 'actualearnings'})
        price_fairvalue['valuation'] = (price_fairvalue['price'] / price_fairvalue['fairvalue'] )
        regression_data = RegressionData(price_fairvalue)
        missing_data = RegressionData(cls.incomplete_data)
        coefficient_data = Coefficients('SP_500', mlr.intercept_, treasury_coef, earnings_coef, dividend_coef, datetime.now())
        file = open('../ml_model_regression.pkl', 'wb')
        pickle.dump(coefficient_data, file)
        pickle.dump(regression_data['price_fairvalue'], file)
        pickle.dump(cls.last_date, file)
        pickle.dump(missing_data, file)
        file.close()
        return {'coefficients': coefficient_data, 'historicaldata': regression_data['price_fairvalue'], 'lastdate': cls.last_date}



