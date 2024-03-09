import pandas as pd
import matplotlib.pyplot as plt
from pandas import DataFrame
import numpy as np


def count_consecutive_sequences(arr: []):
    positive_count = 0
    negative_count = 0

    for num in arr:
        if num > 0:
            positive_count += 1
        elif num <= 0:
            negative_count += 1

    return positive_count, negative_count


def valid_price_change_consecutive(raw_data):
    for line in raw_data:
        del line[8:]
    columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'base_asset_volume']
    df = pd.DataFrame(raw_data, columns=columns)

    # Convert 'open_time' and 'close_time' columns to datetime format
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')

    # Convert numeric columns to appropriate numeric types
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

    # Calculate daily close price change. Calculate the price change
    df['close_change'] = df['close'].diff()
    df['volume_change'] = df['volume'].diff()

    # Calculate the percentile change
    df['close_change_percentile'] = (df['close_change'] / df['close'].shift(1) * 100).round(2)
    df['volume_change_percentile'] = (df['volume_change'] / df['volume'].shift(1) * 100).round(2)

    # Display the DataFrame with the added 'close_change' column
    # print(df[['open_time', 'close', 'close_change', 'close_change_percentile', 'volume', 'volume_change',
    #           'volume_change_percentile']])

    percentile_price_change = df['close_change_percentile'][1:].to_numpy()
    pos_count, neg_count = count_consecutive_sequences(percentile_price_change)

    # only buy if the previous cycle is down
    if neg_count - pos_count >= 1:
        print(f'Buy. {percentile_price_change}')
        return True
    else:
        print(f'DONT Buy. {percentile_price_change}')
        return False


def build_dataframe(raw_data):
    for line in raw_data:
        del line[5:]
    #  2 dimensional tabular data
    df = pd.DataFrame(raw_data, columns=['date', 'open', 'high', 'low', 'close'])
    return df


def bollinger_bands(symbol_df: DataFrame):
    period = 10

    # small-time Moving average. calculate 20 moving averages using Pandas over close price
    symbol_df['sma'] = symbol_df['close'].rolling(period).mean()
    # Get standard deviation
    symbol_df['std'] = symbol_df['close'].rolling(period).std()
    # Calculate an Upper Bollinger band
    symbol_df['upper'] = symbol_df['sma'] + (2 * symbol_df['std'])
    # Calculate a Lower Bollinger band
    symbol_df['lower'] = symbol_df['sma'] - (2 * symbol_df['std'])

    # Prepare buy and sell signals. The lists prepared are still panda data frames with float nos
    close_list = pd.to_numeric(symbol_df['close'], downcast='float')
    upper_list = pd.to_numeric(symbol_df['upper'], downcast='float')
    lower_list = pd.to_numeric(symbol_df['lower'], downcast='float')
    symbol_df['buy'] = np.where(close_list < lower_list, symbol_df['close'], np.NaN)
    symbol_df['sell'] = np.where(close_list > upper_list, symbol_df['close'], np.NaN)

    # To print in human-readable date and time (from timestamp)
    symbol_df.set_index('date', inplace=True)
    symbol_df.index = pd.to_datetime(symbol_df.index, unit='ms')
    # with open('output.txt', 'w') as f:
    #     f.write(symbol_df.to_string())
    return symbol_df


def plot_graph(df):
    df = df.astype(float)
    df[['close', 'upper', 'lower']].plot()
    plt.xlabel('Date', fontsize=18)
    plt.ylabel('Close price', fontsize=18)
    x_axis = df.index
    plt.fill_between(x_axis, df['lower'], df['upper'], color='grey', alpha=0.30)

    plt.scatter(df.index, df['buy'], color='purple', label='Buy', marker='^', alpha=1)  # purple = buy
    plt.scatter(df.index, df['sell'], color='red', label='Sell', marker='v', alpha=1)  # red = sell

    plt.show()
