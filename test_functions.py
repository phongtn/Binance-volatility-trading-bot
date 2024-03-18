import time
from datetime import datetime, timedelta, time

from binance.helpers import round_step_size

import utilities.time_util
from binance_api_wrapper import BinanceAPIWrapper
# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)
# Load helper modules
from helpers.parameters import (
    load_config
)
from publish.EventListeners import NotionListeners, TeleListeners
from publish.EventManager import EventManager

coins_bought = {'BTC': {'take_profit': 2, 'stop_loss': -1, 'volume': 55}}
parsed_config = load_config('test.config.yml')
parsed_creds = load_config('creds.yml')
FIATS = parsed_config['trading_options']['FIATS']

access_key, secret_key = load_correct_creds(parsed_creds, TEST=True)

client = BinanceAPIWrapper(access_key, secret_key)


# client.API_URL = client.API_TESTNET_URL


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


def get_balance(symbol: str):
    try:
        balance = client.get_asset_balance(asset=symbol)
        free = balance.get('free')
        return float(free)
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


def test_notification():
    notion = NotionListeners()
    tele = TeleListeners()

    event_manger = EventManager()
    event_manger.attach(notion)
    event_manger.attach(tele)

    event_manger.state = 2
    event_manger.notify()


def wait_for_order_completion(coin):
    """in PROD mode, we'll get the latest order from history to ensure the order is placed."""
    """Wait for the order to be completed and return the order details."""
    latest_order = client.get_all_orders(symbol=coin, limit=1)
    retry = 1
    while not latest_order and retry <= 5:
        print(f'Binance is slow in returning the order and calling the API again... times {retry}.')
        latest_order = client.get_all_orders(symbol=coin, limit=1)
        time.sleep(1)
        retry += 1

    return latest_order


def standard_volume(symbol: str, vol):
    try:
        info = client.get_symbol_info(symbol)
        step_size = info['filters'][1]['stepSize']
        print(step_size)
        return round_step_size(vol, step_size)
    except Exception as exception:
        print(f'convert volume failed: {exception}')


def get_klines(symbol: str):
    end = datetime.now()
    start = (end - timedelta(days=float(1))).timestamp()
    print(utilities.time_util.convert_timestamp(start))
    print(utilities.time_util.convert_timestamp(end.timestamp()))
    return client.get_klines(symbol=symbol, interval='1m', startTime=int(start * 1000),
                             endTime=int(end.timestamp() * 1000))


def count_consecutive_sequences(arr):
    consecutive_positives = 0
    consecutive_negatives = 0
    current_sequence = 0

    for i in range(1, len(arr)):
        if arr[i] > arr[i - 1]:
            current_sequence += 1
        else:
            current_sequence = 0

        if current_sequence > 0 and arr[i] > 0:
            consecutive_positives = max(consecutive_positives, current_sequence)
        elif current_sequence > 0 and arr[i] < 0:
            consecutive_negatives = max(consecutive_negatives, current_sequence)

    return consecutive_positives, consecutive_negatives


if __name__ == '__main__':
    symbol = 'BNB' + 'USDT'
    end = datetime.now()
    start = (end - timedelta(days=float(10))).timestamp()
    today = datetime.now().date()

    custom_time = datetime.combine(today, time(hour=10, minute=48))
    # time_diff = datetime.now() - timedelta(minutes=3)
    # raw_data = client.get_klines_minutes(symbol, '1m', 60 * 3, custom_time)
    # pricesignal.valid_price_change_consecutive(raw_data=raw_data)
    # backtesting.sma_trade_logic(raw_data)

    # sma
    # bars = client.get_historical_klines(symbol, client.KLINE_INTERVAL_3MINUTE, '1 day ago UTC')
    # bars = client.get_klines_minutes(symbol, '3m', 60 * 3)
    # pricesignal.valid_price_change_consecutive(raw_data=bars)
    # backtesting.sma_trade_logic(bars)
    # pricesignal.valid_price_change_consecutive(raw_data=raw_data)
    # df = pricesignal.build_dataframe(bars)
    # df = pricesignal.bollinger_bands(df)
    # print(df.head(20))

    # df.to_csv(f'data/{symbol}_3m_oneday.csv', encoding='utf-8')
