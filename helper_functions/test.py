import python_finance as pf


def main():
    tickers = ['AAPL', 'MSFT', 'NFLX', 'AMZN', 'GOOG']
    tickers_b = ['DOCU', 'SHOP', 'WMT']
    start = '20200101'
    end = '20201007'
    attrib = 'Adj Close'
    
    #print(pf.get_tickers(tickers, start, end, attrib))
    #print(pf.get_Percent_change(tickers, start, end, attrib))
    #print(pf.get_Mean_Daily_Return(tickers, start, end, attrib))
    #print(pf.get_Cov_Matrix(tickers, start, end, attrib))
    print(pf.get_tickers(tickers_b, start, end, attrib))
    print(pf.get_Percent_change(tickers_b, start, end, attrib))
    mean_returns =  pf.get_Mean_Daily_Return(tickers_b, start, end, attrib)
    print(mean_returns)
    cov = pf.get_Cov_Matrix(tickers_b, start, end, attrib)
    print(cov)
    num_portfolios = 100000
    rf = 0
    print(pf.simulate_random_portfolios(num_portfolios, mean_returns, cov, rf, tickers_b))

if __name__ == "__main__":
    main()