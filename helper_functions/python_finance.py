import json
import logging
import logging.config
import os, sys, inspect, time
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PARENT_DIR, 'helper_functions'))
import pandas as pd  
import numpy as np
from pandas_datareader import data, wb
import datetime
import scipy.optimize as sco
from scipy import stats


def get_latest_week_date(date):
    ret_date = date
    return ret_date

def get_tickers(tickers, start, end, attrib):
    ticker_data = pd.DataFrame([get_ticker_data(x.strip(), start, end)[attrib] for x in tickers]).T
    ticker_data.columns = tickers
    return ticker_data

def get_ticker_data(ticker, start, end):
    #print('{},  {},  {}' .format(ticker, start, end))
    ticker_data = data.DataReader(ticker, 'yahoo', start, end)
    ticker_data.sort_values(by='Date') 
    return ticker_data

def get_Percent_change(ticker, start, end, attrib):
    ticker_data = get_tickers(ticker,start, end, attrib)
    return_data = ticker_data.pct_change()
    return_data.round(6)
    return return_data

def get_Mean_Daily_Return(ticker, start, end, attrib):
    ticker_data = get_Percent_change(ticker,start, end, attrib)
    #print('ticker_data type {}, data{}' .format(type(ticker_data), ticker_data))
    return_data = ticker_data.round(6)
    #print('return_data type {}, data{}' .format(type(return_data), return_data))
    mean_daily_returns = return_data.mean()
    #print('mean_daily_returns type {}, data{}' .format(type(mean_daily_returns), mean_daily_returns))
    return mean_daily_returns

def get_Cov_Matrix(ticker, start, end, attrib):
    ticker_data = get_Percent_change(ticker,start, end, attrib)
    return_data = ticker_data.round(6)
    cov_matrix = return_data.cov()
    return cov_matrix

def calc_portfolio_perf(weights, mean_returns, cov, rf):
    portfolio_return = np.sum(mean_returns * weights) * 252
    portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov, weights))) * np.sqrt(252)
    sharpe_ratio = (portfolio_return - rf) / portfolio_std
    return portfolio_return, portfolio_std, sharpe_ratio


def simulate_random_portfolios(num_portfolios, mean_returns, cov, rf,tickers):
    print("JRP mean {} type {}" .format(mean_returns, type(mean_returns)))
    num_portfolios = int(num_portfolios)
    rf = float(rf)
    results_matrix = np.zeros((len(mean_returns)+3, num_portfolios))
    print("JRP result_matrix {} type {}" .format(results_matrix, type(results_matrix)))
    for i in range(num_portfolios):
        weights = np.random.random(len(mean_returns))
        weights /= np.sum(weights)
        portfolio_return, portfolio_std, sharpe_ratio = calc_portfolio_perf(weights, mean_returns, cov, rf)
        results_matrix[0,i] = portfolio_return
        results_matrix[1,i] = portfolio_std
        results_matrix[2,i] = sharpe_ratio
        #iterate through the weight vector and add data to results array
        for j in range(len(weights)):
            results_matrix[j+3,i] = weights[j]
            
    results_df = pd.DataFrame(results_matrix.T,columns=['ret','stdev','sharpe'] + [ticker for ticker in tickers])
    results_df['portfolio_id'] = results_df.index
    output_df = results_df.melt(id_vars=['portfolio_id','ret', 'stdev', 'sharpe'], var_name='Ticker', value_name='percentage')
        
    return output_df, results_df