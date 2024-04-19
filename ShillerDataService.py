import json
import os
import time
import urllib

import numpy as np
import pandas as pd
import pickle
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn import metrics

from CoefficientData import CoefficientData
from RegressionData import RegressionData


class ShillerDataService:
    schiller_data_url = "http://www.econ.yale.edu//~shiller/data/ie_data.xls"
    file = "test_11.xls"
    shiller_df = pd.DataFrame()

    @classmethod
    def download_shiller_data(cls):
        if not os.path.exists(cls.file):
            urllib.request.urlretrieve(cls.schiller_data_url, cls.file)
        else:
            modified = os.path.getmtime(cls.file)
            dayssince = (time.time() - modified) / 3600 / 24
            if dayssince > 10:
                urllib.request.urlretrieve(cls.schiller_data_url, cls.file)

        df = pd.read_excel(cls.file, sheet_name='Data', skiprows=range(0, 7), skipfooter=1, usecols='A:D,G:I,K')
        df['D'].replace('', np.nan, inplace=True)
        df['Dividend'].replace('', np.nan, inplace=True)
        df['Earnings'].replace('', np.nan, inplace=True)
        df['E'].replace('', np.nan, inplace=True)
        df.dropna(subset=['Dividend', 'Earnings', 'D', 'E'], inplace=True)
        df['Date'] = df['Date'].astype(str).replace('\.', '/', regex=True).apply(lambda x: x + '0' if len(x) == 6 else x).apply(lambda x: x + '/01')

        # drop all rows before Jan 1, 1960
        # i = 1068
        i = df.index[df['Date'] == '1900/01/01'].tolist()[0]
        # i = 4
        cls.shiller_df = df.drop(df.index[:i])
        return cls.shiller_df

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
        coefficient_data = CoefficientData('SP_500', mlr.intercept_, dividend_coef, earnings_coef, treasury_coef)
        pickle.dump(coefficient_data, open('ml_model.pkl', 'wb'))
        return {'coefficients': coefficient_data, 'historicaldata': regression_data['price_fairvalue']}

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
        coefficient_data = CoefficientData('SP_500', mlr.intercept_, dividend_coef, earnings_coef, treasury_coef)
        pickle.dump(coefficient_data, open('ml_model.pkl', 'wb'))
        return {'coefficients': coefficient_data, 'historicaldata': regression_data['price_fairvalue']}



