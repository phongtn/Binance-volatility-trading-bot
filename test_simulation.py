from datetime import datetime

import pytz

import data.simulator as sim
from binance_api_wrapper import BinanceAPIWrapper
from helpers.handle_creds import load_correct_creds
from helpers.parameters import load_config
from binance.exceptions import BinanceAPIException

parsed_creds = load_config('creds.yml')
access_key, secret_key = load_correct_creds(parsed_creds, TEST=True)
client = BinanceAPIWrapper(access_key, secret_key)

if __name__ == '__main__':
    symbol = 'BNB' + 'USDT'
    start_time = int(datetime(2024, 3, 11, tzinfo=pytz.timezone('UTC')).timestamp() * 1000)
    end_time = int(datetime(2024, 3, 12, tzinfo=pytz.timezone('UTC')).timestamp() * 1000)

    tickers = [line.strip() for line in open('big_tickers.txt')]
    for ticker in tickers:
        try:
            raw_data = client.get_historical_klines(symbol=ticker + 'USDT',
                                                    interval='3m',
                                                    start_str=start_time,
                                                    end_str=end_time)
            print(f'============={ticker}================')
            sim.back_testing(raw_data=raw_data)
        except BinanceAPIException as ex:
            print(f'Exception {ticker}: {ex}')