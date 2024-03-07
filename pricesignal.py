import datetime

import pandas as pd

import utilities.time_util


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

    if pos_count - neg_count > 0:
        print(f'DONT Buy. {percentile_price_change}')
        return False
    else:
        print(f'Buy. {percentile_price_change}')
        return True
