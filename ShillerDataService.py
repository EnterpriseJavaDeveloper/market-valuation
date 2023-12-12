import json
import os
import urllib
import pandas as pd
import pickle
from sklearn.linear_model import LinearRegression

from RegressionData import RegressionData


class ShillerDataService:
    schiller_data_url = "http://www.econ.yale.edu//~shiller/data/ie_data.xls"
    file = "test_12.xls"
    shiller_df = pd.DataFrame()

    @classmethod
    def download_shiller_data(cls):
        if not os.path.exists(cls.file):
            urllib.request.urlretrieve(cls.schiller_data_url, cls.file)  # For Python 3
        df = pd.read_excel(cls.file, sheet_name='Data', skiprows=range(0, 7), skipfooter=5, usecols='A,G:I,K')
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
        regression_data = RegressionData('SP_500', mlr.intercept_, dividend_coef, earnings_coef, treasury_coef,
                                         price_fairvalue)

        pickle.dump(regression_data, open('ml_model.pkl', 'wb'))
        return regression_data
