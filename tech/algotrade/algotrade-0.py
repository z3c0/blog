import configparser
import pandas as pd
import numpy as np

config = configparser.ConfigParser()
config.read('algotrade.cfg')

EOD_API_KEY = config['eodhistoricaldata']['api_key']
WATCHLIST_PATH = 'tech/algotrade/algotrade-0.csv'


def download_stock_data(ticker):
    endpoint = (f'https://eodhistoricaldata.com/api/eod/{ticker}.US'
                f'?api_token={EOD_API_KEY}'
                '&fmt=json')

    history_df = pd.read_json(endpoint, convert_dates=True)
    return history_df


def process_stocks():
    watchlist_df = pd.read_csv(WATCHLIST_PATH)

    history_list = list()
    for symbol in watchlist_df['symbol']:
        history_df = download_stock_data(symbol)
        history_df['symbol'] = symbol
        history_list.append(history_df)

    history_df = pd.concat(history_list)
    history_df = history_df.reset_index()

    history_df = history_df.set_index(['symbol', 'date'])
    mkt_close = history_df[['close']].unstack('symbol')
    mkt_close = pd.DataFrame(mkt_close['close'])

    # daily statistics
    daily_change = mkt_close - mkt_close.shift(1)
    daily_direction = np.sign(daily_change)
    daily_returns = daily_change.cumsum()

    # monthly statistics
    monthly_mkt_close = mkt_close.resample('M').last()
    monthly_change = monthly_mkt_close - monthly_mkt_close.shift(1)
    monthly_direction = np.sign(monthly_change)
    monthly_returns = monthly_change.cumsum()

    # quarterly statistics
    quarterly_mkt_close = mkt_close.resample('3M').last()
    quarterly_change = quarterly_mkt_close - quarterly_mkt_close.shift(1)
    quarterly_returns = quarterly_change.cumsum()

    # momentum - daily
    momentum = dict()
    for period in [3, 21, 126, 252]:
        momentum[f'momentum_daily_{period}'] = \
            daily_direction.rolling(period).sum()

    # momentum - monthly
    for period in [3, 6, 9, 12]:
        momentum[f'momentum_monthly_{period}'] = \
            monthly_direction.rolling(period).sum()

    # simple moving average - daily
    simple_moving_average = dict()
    for period in [21, 42, 126, 252]:
        simple_moving_average[f'sma_daily_{period}'] = \
            daily_returns.rolling(period).mean()

    # simple moving average - monthly
    for period in [3, 6, 12, 24]:
        simple_moving_average[f'sma_monthly_{period}'] = \
            monthly_returns.rolling(period).mean()

    # lagged returns - daily
    lagged_returns = dict()
    for period in [3, 8, 21]:
        lag_df = pd.DataFrame()

        for symbol in daily_returns.columns:
            for lag in range(period + 1):
                lag_df[symbol + f'_{lag}'] = daily_returns[symbol].shift(lag)

        lagged_returns[f'lag_day_{period}'] = lag_df

    # lagged returns - monthly
    for period in [3, 8, 21]:
        lag_df = pd.DataFrame()

        for symbol in monthly_returns.columns:
            for lag in range(period + 1):
                lag_df[symbol + f'_{lag}'] = monthly_returns[symbol].shift(lag)

        lagged_returns[f'lag_month_{period}'] = lag_df

    # lagged returns - quarterly
    for period in [3, 8, 11, 21]:
        lag_df = pd.DataFrame()

        for symbol in quarterly_returns.columns:
            for lag in range(period + 1):
                lag_df[symbol + f'_{lag}'] = \
                    quarterly_returns[symbol].shift(lag)

        lagged_returns[f'lag_quarter_{period}'] = lag_df

    def write_to_parquet(df, path):
        df.to_parquet(path + '.parquet.gzip', compression='gzip')

    write_to_parquet(mkt_close, 'data/market_close')
    write_to_parquet(daily_returns, 'data/returns_daily')
    write_to_parquet(monthly_returns, 'data/returns_monthly')
    write_to_parquet(quarterly_returns, 'data/returns_quarterly')

    for key in momentum:
        write_to_parquet(momentum[key], f'data/{key}')

    for key in simple_moving_average:
        write_to_parquet(simple_moving_average[key], f'data/{key}')

    for key in lagged_returns:
        write_to_parquet(lagged_returns[key], f'data/{key}')


def backtest_sma_strategy():
    close_price = pd.read_parquet('data/market_close.parquet.gzip')
    daily_returns = pd.read_parquet('data/returns_daily.parquet.gzip')
    short_sma = pd.read_parquet('data/sma_daily_21.parquet.gzip')
    long_sma = pd.read_parquet('data/sma_daily_126.parquet.gzip')

    returns_percent = daily_returns / daily_returns.shift(1)

    buy_signals = np.where(short_sma > long_sma, 1, np.nan)
    buy_signals = pd.DataFrame(buy_signals, columns=close_price.columns)
    buy_signals = buy_signals[buy_signals != buy_signals.shift(1)]
    buy_signals.index = close_price.index

    equity = buy_signals * close_price
    equity = equity.fillna(0).cumsum() * returns_percent

    market = daily_returns.iloc[-1]
    strategy = equity.iloc[-1]

    return strategy, strategy - market


def backtest_momentum_strategy():
    close_price = pd.read_parquet('data/market_close.parquet.gzip')
    daily_returns = pd.read_parquet('data/returns_daily.parquet.gzip')
    momentum = pd.read_parquet('data/momentum_daily_3.parquet.gzip')

    returns_percent = daily_returns / daily_returns.shift(1)

    buy_signals = np.where(momentum > 0, 1, np.nan)
    buy_signals = pd.DataFrame(buy_signals, columns=close_price.columns)
    buy_signals = buy_signals[buy_signals != buy_signals.shift(1)]
    buy_signals.index = close_price.index

    equity = buy_signals * close_price
    equity = equity.fillna(0).cumsum() * returns_percent

    market = daily_returns.iloc[-1]
    strategy = equity.iloc[-1]

    return strategy, strategy - market


if __name__ == '__main__':
    process_stocks()

    sma_strategy, sma_perf = backtest_sma_strategy()
    momentum_strategy, momentum_perf = backtest_momentum_strategy()
    daily_returns = pd.read_parquet('data/returns_daily.parquet.gzip')

    performance = {
        'sma': sma_strategy,
        'momentum': momentum_strategy,
        'market': daily_returns.iloc[-1],
        'sma_vs_momentum': sma_strategy - momentum_strategy,
        'sma_vs_market': sma_perf,
        'momentum_vs_market': momentum_perf
    }

    performance = pd.DataFrame(performance)
    performance.to_excel('backtest.xlsx')
