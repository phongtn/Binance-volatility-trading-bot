import time

from starter import get_price
# needed for the binance API / websockets / Exception handling
from binance.client import Client
from datetime import date, datetime, timedelta

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key
)

import save_history
from base_logger import logger
import signal
import sys


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


coins_bought = {'BTC': {'take_profit': 2, 'stop_loss': -1, 'volume': 55}}
parsed_config = load_config('test.config.yml')
parsed_creds = load_config('creds.yml')
FIATS = parsed_config['trading_options']['FIATS']

access_key, secret_key = load_correct_creds(parsed_creds)

client = Client(access_key, secret_key)
client.API_URL = 'https://testnet.binance.vision/api'


def test_tsl(coin: str, buy_price: float, price: float, USE_TRAILING_STOP_LOSS=True):
    TRADING_FEE = 0.075
    BuyPrice = float(buy_price)
    all_latest_price = {coin: {'price': price}}

    coin_latest_price = float(all_latest_price[coin]['price'])

    TRAILING_TAKE_PROFIT = 0.6
    TRAILING_STOP_LOSS = 0.7

    # change percent
    PriceChange = round(float((coin_latest_price - BuyPrice) / BuyPrice * 100), 2)

    # define stop loss and take profit
    price_take_profit = BuyPrice + (BuyPrice * coins_bought[coin]['take_profit']) / 100
    price_stop_loss = BuyPrice + (BuyPrice * coins_bought[coin]['stop_loss']) / 100

    print(f'Price change: {PriceChange} %. Price SL: {price_stop_loss} and Price TP: {price_take_profit}')

    print(coins_bought)
    # # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
    if coin_latest_price > price_take_profit and USE_TRAILING_STOP_LOSS:
        coins_bought[coin]['take_profit'] = PriceChange + TRAILING_TAKE_PROFIT
        coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
        print(coins_bought)
        print(
            f"{coin} TP reached {BuyPrice}/{coin_latest_price}, change {PriceChange}%. Adjusting TP {coins_bought[coin]['take_profit']:.2f}  "
            f"and SL {coins_bought[coin]['stop_loss']:.2f} accordingly to lock-in profit")

    if coin_latest_price < price_stop_loss or coin_latest_price > price_take_profit and not USE_TRAILING_STOP_LOSS:
        print(
            f"selling {coins_bought[coin]['volume']} {coin} - {BuyPrice} - {coin_latest_price} : {PriceChange - (TRADING_FEE * 2):.2f}% "
            f"Est:${(100 * (PriceChange - (TRADING_FEE * 2))) / 100:.2f}")


def simulate_price_change(coin: str):
    buy_price = 10
    latest_price = buy_price
    for i in range(1, 3):
        latest_price = latest_price + 0.25
        test_tsl(coin, buy_price, latest_price)
        print('------------------------------------------')
        time.sleep(3)

    test_tsl(coin, buy_price, 10.4)


def get_balance():
    try:
        balance = client.get_account()
        free = [b['free'] for b in balance['balances'] if b['asset'] == 'BNBUSDT']
        logger.info(f'BNB: {free}')
    except Exception as exception:
        print(f'get account balance failed. The reason is: {exception}')


def get_little_coins(limit: int):
    prices = client.get_all_tickers()

    f = open('little_tickers.txt', 'w')
    count = 0
    for coin in prices:
        if 'USDT' in coin['symbol'] and all(item not in coin['symbol'] for item in FIATS):
            # only tracking coin have low denomination
            current_price = coin['price']
            if float(current_price) <= limit:
                f.write(coin['symbol'].replace('USDT', ''))
                f.write('\n')
                count = count + 1
    f.close()
    print(f'Total {len(prices)} coins. And filter {count} coins with limit {limit}')


def test_time_difference():
    TIME_DIFFERENCE = 3
    RECHECK_INTERVAL = 3
    time_diff = datetime.now() - timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL))
    print(time_diff)


class BinanceAPIWrapper(Client):
    def rolling_window_price_change(self, pair: str, window: str):
        params = {
            'symbol': pair,
            'windowSize': window
        }
        return self._get('ticker', data=params, version=client.PRIVATE_API_VERSION)


if __name__ == '__main__':
    # simulate_price_change('BTC')
    # get_little_coins(10)
    # sub_client = BinanceAPIWrapper()
    # result = sub_client.rolling_window_price_change('BTCUSDT', '1m')
    # print(result)
    # simulate_price_change('BTC')
    test_time_difference()
