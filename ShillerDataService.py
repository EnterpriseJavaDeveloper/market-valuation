import json
import os
import time
import urllib

import numpy as np
import pandas as pd
import pickle
from sklearn.linear_model import LinearRegression

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

        df = pd.read_excel(cls.file, sheet_name='Data', skiprows=range(0, 7), skipfooter=1, usecols='A,G:I,K')
        df['Dividend'].replace('', np.nan, inplace=True)
        df['Earnings'].replace('', np.nan, inplace=True)
        df.dropna(subset=['Dividend', 'Earnings'], inplace=True)
        df['Date'] = df['Date'].astype(str).replace('\.', '/', regex=True).apply(lambda x: x + '0' if len(x) == 6 else x).apply(lambda x: x + '/01')

        # drop all rows before Jan 1, 1960
        cls.shiller_df = df.drop(df.index[:1068])
        return cls.shiller_df

    @classmethod
    def get_regression_data(cls):
        mlr = LinearRegression()
        mlr.fit(cls.shiller_df[['Dividend', 'Earnings', 'Rate GS10']], cls.shiller_df['Price'])
        cls.shiller_df['FairValue'] = cls.shiller_df.loc[:, 'Dividend'] * mlr.coef_[0] + \
            cls.shiller_df.loc[:, 'Earnings'] * mlr.coef_[1] + cls.shiller_df.loc[:, 'Rate GS10'] * mlr.coef_[2] + \
            mlr.intercept_
        treasury_coef = mlr.coef_[2]
        dividend_coef = mlr.coef_[0]
        earnings_coef = mlr.coef_[1]
        price_fairvalue = cls.shiller_df[['Date', 'Price', 'FairValue', 'Dividend', 'Earnings', 'Rate GS10']]
        price_fairvalue = price_fairvalue.rename(str.lower, axis='columns')
        regression_data = RegressionData(price_fairvalue)
        coefficient_data = CoefficientData('SP_500', mlr.intercept_, dividend_coef, earnings_coef, treasury_coef)
        pickle.dump(coefficient_data, open('ml_model.pkl', 'wb'))
        return {'coefficients': coefficient_data, 'historicaldata': regression_data['price_fairvalue']}
