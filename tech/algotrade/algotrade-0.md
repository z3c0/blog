# Algorithmic Trading

## Intro: A Fool's Errand... If Done Wrong

The stock market is an unpredictable and chaotic world that can be very difficult to wrap one's head around. Conventional wisdom continually assures us of the frivolity of predicting market changes, parroting adages like *"Time in the market is better than timing the market"* or the famous Buffett quote *"The stock market is a device for transferring money from the impatient to the patient"*. With this in mind, algorithmic trading sounds like a pipe dream - a wonderful idea on paper, but doomed to fail in practice. However, this is only when one assumes that algorithmic trading strategies are trying to predict the direction of a stock. In reality, algorithmic trading only seeks to respond quickly to events that have already happened, such as a stock suddenly trending downwards. This practice dates all the way back to 1949, when [Richard Donchian](https://en.wikipedia.org/wiki/Richard_Donchian) pioneered rule-based trading by using [trend following](https://www.investopedia.com/terms/t/trendtrading.asp). He reasoned that measurements like moving averages could be used to discern when a stock's price is moving in a sustained manner, denoting a trend. When a stock is trending upwards, one can buy-in and ride the wave into gains. When the same stock is trending downwards, one can exit gracefully - profits in hand - and avoid the crash. This forever changed stock trading, and allowed traders to harbor more certainty amidst the chaos of the market. The advent of the computer in the following decades only served to bolster this certainty, by allowing more advanced measurements to be performed more quickly than a human trader could. In 1992, with the creation of [Globex](https://en.wikipedia.org/wiki/Globex_Trading_System) by the Chicago Mercantile Exchange, computers shouldered their way past human traders with the newfound ability to place trades directly.

Today, "trade signals" are derived from all over the data-sphere - earnings reports, tweets, interest rates, policy changes, and [even the weather](https://weathersource.com/) could have a salient impact on the sentiment surrounding a security, and thus, its price.

So how does one go about constructing an algorithm that can inform whether to buy, sell, or hold? In this blog series, we'll be digging into exactly that.

## Part 1: Preparing Stock Data for Analysis

### Picking a Data Source

The road to bot-fueled trading is a long one, and one we'll be spending a lot of time on before reaching our destination. As with any data-driven venture, our journey begins with securing our data.

Choosing the right data source can be challenging and/or expensive, so shop around for a data source that's equal parts functional and affordable. Here's a few options, to get you started:

- [EODHistoricalData](https://eodhistoricaldata.com)

- [Quandl](https://www.quandl.com/?mod=article_inline)

- [Polygon.io](https://polygon.io/pricing)

- [Alphavantage](https://www.alphavantage.co)

- [Marketstack](https://marketstack.com)

For the purposes of our exercise, we'll be utilizing the data available from [eodhistoricaldata.com](https://eodhistoricaldata.com). Feel free to use a data source more to your liking. So long as the source you choose has close price history by day, you should be able easily emulate the steps of this tutorial.

### Downloading the Data

We can easily download data by utilizing the Pandas function `read_json`.

``` python
import configparser
import pandas as pd

config = configparser.ConfigParser()
config.read('algotrade.cfg')

EOD_API_KEY = config['eodhistoricaldata']['api_key']

def download_stock_data(ticker):
    endpoint = (f'https://eodhistoricaldata.com/api/eod/{ticker}.US'
                f'?api_token={EOD_API_KEY}'
                '&fmt=json')

    history_df = pd.read_json(endpoint, convert_dates=True)
    return history_df

```

The `download_stock_data` function is designed to take a single stock symbol and download its historical EOD data into a Pandas `DataFrame`. Next, we'll need to define which stocks we would like to download data for. How you procure your list is up to you - but for our purposes, it would be best stored in a CSV alongside your script.

``` txt
symbol,name
AACQ,ARTIUS ACQUISITION INC
AAN,AARONS COMPANY INC
AAPL,APPLE INC
ABC,AMERISOURCEBERGEN CORP
...
VRTX,VERTEX PHARMACEUTICALS INC
VXRT,VAXART INC
WATT,ENERGOUS CORP
ZY,ZYMERGEN INC
```

Let's add the CSV's location to a constant at the top of our script.

``` python
EOD_API_KEY = config['eodhistoricaldata']['api_key']
WATCHLIST_PATH = 'tech/algotrade/algotrade-0.csv'
```

Afterwards, we can load our CSV using the Pandas `read_csv` function.

``` python

def process_stocks():
    watchlist_df = pd.read_csv(WATCHLIST_PATH)

```

Now that we have our stock symbols, we can start downloading our data into a single list.

``` python

def process_stocks():
    watchlist_df = pd.read_csv(WATCHLIST_PATH)

    history_list = list()
    for symbol in watchlist_df['symbol']:
        history_df = download_stock_data(symbol)
        history_df['symbol'] = symbol
        history_list.append(history_df)
```

Once our list has been populated, we can union all of our `DataFrames` by using the `concat` function. Calling the `reset_index` function afterwards will remove the duplicate indexes the union will create.

``` python
    history_df = pd.concat(history_list)
    history_df = history_df.reset_index()
```

After resetting our index, we will need to create a new one that denotes the identity of each row. Every row is a date per stock symbol, so we will set our index to use `symbol` and `date`.

``` python
    history_df = history_df.set_index(['symbol', 'date'])
```

Once we've set our index, we can pivot our dataset to make the rows more unique. Ideally, we should have a matrix where each cell is the close price per stock per date. This can be achieved by selecting the "close" `Series` and subsequently using the `unstack` function. Afterwards, all our symbols will be arranged horizontally under a single `Series` "close". By selecting this `Series`, and converting it to a `DataFrame`, we'll be left with a matrix of *n* columns by *i* rows, where *n* is the number of symbols and *i* is each individual date that we have a close price for.

``` python
    mkt_close = history_df[['close']].unstack('symbol')
    mkt_close = pd.DataFrame(mkt_close['close'])
```

Once our data is arranged as a matrix, we can easily perform calculations against it.

``` python

    # daily statistics

    # the difference in price between each day
    daily_change = mkt_close - mkt_close.shift(1)

    # the price direction of each day
    # +1 for up, -1 for down, 0 for no change
    daily_direction = np.sign(daily_change)

    # the cumulative returns of each stock 
    daily_returns = daily_change.cumsum()

```

Once we've performed our basic calculations, we will use them to calculate more useful statistics, such as [simple moving averages](https://www.investopedia.com/terms/s/sma.asp) and [momentum](https://www.investopedia.com/terms/m/momentum.asp).

Given the openendedness of these calculations, we can perform the calculations multiple times with different parameters. We will choose our parameters by the number of trading days that we want to find trends over.

Three trading days is commonly used to determine the immediate momentum of a stock, but larger periods can be used to discern longer-term trends, like 21 (~one month), 126 (~six months), or 252 (~one year).

For our simple moving averages, larger periods tend to be more useful. The shorter the period, the more responsive the curve will be to short-term changes. Longer periods will result in a more gentle curve that changes more slowly over time. This is useful for seeing the short-term trend of a stock against its long-term trend. During a period in which a short-term SMA is higher than the long-term SMA, it can be reasoned that the stock is in a period of growth - vice versa is a period of decline.

``` python
    # momentum - daily
    momentum = dict()
    for period in [3, 21, 126, 252]:
        momentum[f'momentum_daily_{period}'] = \
            daily_direction.rolling(period).sum()

    # simple moving average - daily
    simple_moving_average = dict()
    for period in [21, 42, 126, 252]:
        simple_moving_average[f'sma_daily_{period}'] = \
            daily_returns.rolling(period).mean()
```

After we've performed our calculations, we can write our data to storage.

``` python

    def write_to_parquet(df, path):
        df.to_parquet(path + '.parquet.gzip', compression='gzip')

    write_to_parquet(mkt_close, 'data/market_close')
    write_to_parquet(daily_returns, 'data/returns_daily')

    for key in momentum:
        write_to_parquet(momentum[key], f'data/{key}')

    for key in simple_moving_average:
        write_to_parquet(simple_moving_average[key], f'data/{key}')

```

Now that we've stored our data, we can begin devising strategies. Before we can commit to any given strategy, we should perform backtesting - a process for determining how effective our strategy would have been in a historical context. If our strategies perform well historically, it's reasonable to expect it to respond well to events that have yet to happen (though this is not a guarantee). Constructing backtests can be a challenging task with repercussions if done hastily. How to design, run, and measure the performance of backtests will be the topic of the next entry of this series.
