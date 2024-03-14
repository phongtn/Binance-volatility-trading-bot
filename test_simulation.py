from datetime import datetime

import pytz

import data.simulator as sim
import pandas as pd
from binance_api_wrapper import BinanceAPIWrapper
from helpers.handle_creds import load_correct_creds
from helpers.parameters import load_config
from binance.exceptions import BinanceAPIException

parsed_creds = load_config('creds.yml')
access_key, secret_key = load_correct_creds(parsed_creds, TEST=True)
client = BinanceAPIWrapper(access_key, secret_key)

if __name__ == '__main__':
    symbol = 'BNB' + 'USDT'
    start_time = int(datetime(2024, 3, 13, tzinfo=pytz.timezone('UTC')).timestamp() * 1000)
    end_time = int(datetime(2024, 3, 14, tzinfo=pytz.timezone('UTC')).timestamp() * 1000)

    # tickers = [line.strip() for line in open('big_tickers.txt')]
    tickers = [symbol]
    results = []
    for ticker in tickers:
        try:
            raw_data = client.get_historical_klines(symbol=ticker,
                                                    interval='3m',
                                                    start_str=start_time,
                                                    end_str=end_time)
            total_trades_updated, total_profits_updated, total_losses_updated, asset_remaining, win_rate_updated = (
                sim.back_testing(raw_data=raw_data))
            results.append([ticker, total_trades_updated, total_profits_updated, total_losses_updated, asset_remaining,
                            win_rate_updated])
        except BinanceAPIException as ex:
            print(f'Exception {ticker}: {ex}')

    df = pd.DataFrame(results,
                      columns=['Symbol', 'count_trades', 'total_profits', 'total_losses', 'asset_remaining',
                               'win_rate'])
    print(df.head(10))
