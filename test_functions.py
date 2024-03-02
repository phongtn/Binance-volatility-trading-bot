import sys
import time
from datetime import datetime, timedelta

# needed for the binance API / websockets / Exception handling
from binance.client import Client

from base_logger import logger
# Load creds modules
from helpers.handle_creds import (
    load_correct_creds
)
# Load helper modules
from helpers.parameters import (
    load_config
)
from utilities.make_color import TxColors


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


coins_bought = {'BTC': {'take_profit': 2, 'stop_loss': -1, 'volume': 55}}
parsed_config = load_config('test.config.yml')
parsed_creds = load_config('creds.yml')
FIATS = parsed_config['trading_options']['FIATS']

access_key, secret_key = load_correct_creds(parsed_creds)

client = Client(access_key, secret_key)
# client.API_URL = 'https://testnet.binance.vision/api'


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
        balance = client.get_asset_balance(asset='USDT')
        # free = [b['free'] for b in balance['balances'] if b['asset'] == 'USDT']
        # logger.info(f'BNB: {free}')
        logger.info(balance)
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


def test_notification():
    notion = NotionListeners()
    tele = TeleListeners()

    event_manger = EventManager()
    event_manger.attach(notion)
    event_manger.attach(tele)

    event_manger.state = 2
    event_manger.notify()


from publish.EventManager import EventManager
from publish.EventListeners import NotionListeners, TeleListeners
def calc_trading_profit(buy_price, sell_price, vol):
    """double fee for buy and sell"""
    est_fee = TRADING_FEE / 100 * vol
    # est_fee =  TRADING_FEE / 50 * sell_price * vol
    est_profit = (sell_price - buy_price) * vol - est_fee
    return est_fee, est_profit

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

if __name__ == '__main__':
    result = wait_for_order_completion('PEPEUSDT')
    print(result)
    # get_balance()
    # simulate_price_change('BTC')
    # get_little_coins(10)
    # sub_client = BinanceAPIWrapper()
    # result = sub_client.rolling_window_price_change('BTCUSDT', '1m')
    # print(result)
    # simulate_price_change('BTC')
    # test_time_difference()

    # test_tele_bot()
    TIME_DIFFERENCE = 3
    RECHECK_INTERVAL = 6
    HISTORICAL_PRICES = [None] * (TIME_DIFFERENCE * RECHECK_INTERVAL)
    # print(HISTORICAL_PRICES)
    # print(timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)))
    # test_notification()

    # print(datetime.now() - last_send_tele_mess)
    # print(timedelta(minutes=float()))

    volume = 143595
    TRADING_FEE = 0.075
    # QUANTITY = 100
    BuyPrice = 0.0003482
    coin_latest_price = 0.0003557
    est_fee = TRADING_FEE / 100 * (coin_latest_price * volume)
    percentile_price_change = float((coin_latest_price - BuyPrice) / BuyPrice * 100)

    # print(f'{est_fee * 2} and {TRADING_FEE / 50 * coin_latest_price * volume}')
    # est_profit = (coin_latest_price * volume) - est_fee * 2 - (BuyPrice * volume)
    est_profit = (coin_latest_price * volume) - (BuyPrice * volume) - est_fee * 2
    est_profit_2 = (coin_latest_price - BuyPrice) * volume - (TRADING_FEE / 50 * coin_latest_price * volume)
    profit = ((coin_latest_price - BuyPrice) * volume) * (1 - TRADING_FEE * 2)
    # print(f"est profit: {est_profit}")
    # print(f"est profit 2: {est_profit_2}")
    # print(profit)
    #
    # tx_color = TxColors.SELL_PROFIT if percentile_price_change >= 0. else TxColors.SELL_LOSS
    # print(f"{tx_color}TP or SL reached, "
    #       f"selling {volume} 1000SATSUSDT at price: {BuyPrice}/{coin_latest_price}."
    #       f" Change: {percentile_price_change:.2f}%. Fee: {est_fee:.5f}."
    #       f" Est profit: ${profit:.2f} {est_profit:.2f}")
    #
    # print(calc_trading_profit(2.6073, 2.6073, 383))
