"""
Disclaimer

All investment strategies and investments involve risk of loss.
Nothing contained in this program, scripts, code or repository should be
construed as investment advice.Any reference to an investment's past or
potential performance is not, and should not be construed as, a recommendation
or as a guarantee of any specific outcome or profit.

By using this program, you accept all liabilities,
and that no claims can be made against the developers,
or others connected with the program.
"""

# used for directory handling
import glob
import importlib
import os
import sys
import threading
import json
import time
import signal
import save_history
import utilities.time_util

from datetime import datetime, timedelta
from utilities.time_util import convert_timestamp
from binance.client import Client
from binance.exceptions import BinanceAPIException
from requests.exceptions import ReadTimeout, ConnectionError
from binance_api_wrapper import BinanceAPIWrapper

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key
)

from repository.trading_log import TradingLog
from utilities.make_color import St_ampe_dOut, txcolors
from tasignal import ta_signal_check

# Needed for colorful console output
# Installation with: python3 -m pip install colorama (Mac/Linux) or pip install colorama (PC)
from colorama import init

init()

# tracks profit/loss each session
global session_profit
session_profit = 0

sys.stdout = St_ampe_dOut(sys.stdout)


def get_price(add_to_historical=True):
    """Return the current price for all coins on binance"""

    global HISTORICAL_PRICES, hsp_head
    initial_price = {}
    prices = client.get_all_tickers()

    for coin in prices:

        if CUSTOM_LIST:
            if any(item + PAIR_WITH == coin['symbol'] for item in tickers) and all(
                    item not in coin['symbol'] for item in FIATS):
                initial_price[coin['symbol']] = {'price': coin['price'], 'time': datetime.now()}
        else:
            if PAIR_WITH in coin['symbol'] and all(item not in coin['symbol'] for item in FIATS):
                current_price = coin['price']
                initial_price[coin['symbol']] = {'price': current_price, 'time': datetime.now()}

    if add_to_historical:
        hsp_head += 1

        if hsp_head == RECHECK_INTERVAL:
            hsp_head = 0

        HISTORICAL_PRICES[hsp_head] = initial_price

    return initial_price


def wait_for_price():
    """calls the initial price and ensures the correct amount of time has passed
    before reading the current price again"""

    global HISTORICAL_PRICES, hsp_head, volatility_cooloff

    volatile_coins = {}
    externals = {}

    coins_up = 0
    coins_down = 0
    coins_unchanged = 0

    pause_bot()

    # print(historical prices: {HISTORICAL_PRICES}')
    time_milestone = HISTORICAL_PRICES[hsp_head]['BNB' + PAIR_WITH]['time']
    time_past = datetime.now() - timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL))
    if time_milestone > time_past:
        # sleep for exactly the amount of time required
        time.sleep((timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)) - (
                datetime.now() - time_milestone)).total_seconds())

    print(f'Working...Session profit:{session_profit:.2f}% Est:${(QUANTITY * session_profit) / 100:.2f}')

    # retrieve latest prices
    get_price()

    # calculate the difference in prices
    for coin in HISTORICAL_PRICES[hsp_head]:

        # minimum and maximum prices over time period
        min_price = min(HISTORICAL_PRICES, key=lambda x: float("inf") if x is None else float(x[coin]['price']))
        max_price = max(HISTORICAL_PRICES, key=lambda x: -1 if x is None else float(x[coin]['price']))

        threshold_check = ((-1.0 if min_price[coin]['time'] > max_price[coin]['time'] else 1.0) *
                           (float(max_price[coin]['price']) - float(min_price[coin]['price']))
                           / float(min_price[coin]['price']) * 100)

        # each coin with higher gains than our CHANGE_IN_PRICE
        # is added to the volatile_coins dict if less than MAX_COINS is not reached.
        if threshold_check > CHANGE_IN_PRICE:
            coins_up += 1

            if coin not in volatility_cooloff:
                volatility_cooloff[coin] = datetime.now() - timedelta(minutes=TIME_DIFFERENCE)

            # only include the coin as volatile if it hasn't been picked up in the last TIME_DIFFERENCE minutes already
            if datetime.now() >= volatility_cooloff[coin] + timedelta(minutes=TIME_DIFFERENCE):
                # disable to include coin continue pump
                # volatility_cooloff[coin] = datetime.now()

                # add coin into list coins bought
                if len(coins_bought) + len(volatile_coins) < MAX_COINS or MAX_COINS == 0:
                    volatile_coins[coin] = round(threshold_check, 3)
                    print(f'{coin} has gained {volatile_coins[coin]}% '
                          f'within the last {TIME_DIFFERENCE} minutes, calculating volume in {PAIR_WITH}')
                else:
                    print(f'{txcolors.WARNING}{coin} has gained {round(threshold_check, 3)}% '
                          f'within the last {TIME_DIFFERENCE} minutes, '
                          f'but you are holding max number of coins{txcolors.DEFAULT}')

        elif threshold_check < CHANGE_IN_PRICE:
            coins_down += 1
        else:
            coins_unchanged += 1

    # Disabled until fix
    # print(f'Up: {coins_up} Down: {coins_down} Unchanged: {coins_unchanged}')

    # Here goes new code for external signalling
    externals = external_signals()
    exnumber = 0

    for excoin in externals:
        if excoin not in volatile_coins and excoin not in coins_bought and \
                (len(coins_bought) + exnumber + len(volatile_coins)) < MAX_COINS:
            volatile_coins[excoin] = 1
            exnumber += 1
            print(f'External signal received on {excoin}, calculating volume in {PAIR_WITH}')

    return volatile_coins, len(volatile_coins), HISTORICAL_PRICES[hsp_head]


def external_signals():
    external_list = {}
    signals = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.exs")
    for filename in signals:
        for line in open(filename):
            symbol = line.strip()
            external_list[symbol] = symbol
        try:
            os.remove(filename)
        except:
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}')

    return external_list


def pause_bot():
    """Pause the script when external indicators detect a bearish trend in the market"""
    global bot_paused, session_profit, hsp_head

    # start counting for how long the bots been paused
    start_time = time.perf_counter()

    while os.path.isfile("signals/paused.exc"):

        if bot_paused == False:
            print(f'{txcolors.WARNING}Pausing buying due to change in market conditions, '
                  f'stop loss and take profit will continue to work...{txcolors.DEFAULT}')
            bot_paused = True

        # Sell function needs to work even while paused
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)
        get_price(True)

        # pausing here
        if hsp_head == 1: print(
            f'Paused...Session profit:{session_profit:.2f}% Est:${(QUANTITY * session_profit) / 100:.2f}')
        time.sleep((TIME_DIFFERENCE * 60) / RECHECK_INTERVAL)

    else:
        # stop counting the pause time
        stop_time = time.perf_counter()
        time_elapsed = timedelta(seconds=int(stop_time - start_time))

        # resume the bot and ser pause_bot to False
        if bot_paused == True:
            print(
                f'{txcolors.WARNING}Resuming buying due to change in market conditions, total sleep time: {time_elapsed}{txcolors.DEFAULT}')
            bot_paused = False

    return


def convert_volume():
    """Converts the volume given in QUANTITY from USDT to the coin's volume"""

    volatile_coins, number_of_coins, last_price = wait_for_price()
    lot_size = {}
    volume = {}

    for coin in volatile_coins:

        # Find the correct step size for each coin
        # max accuracy for BTC for example is 6 decimal points
        # while XRP is only 1
        try:
            info = client.get_symbol_info(coin)
            step_size = info['filters'][1]['stepSize']
            lot_size[coin] = step_size.index('1') - 1

            if lot_size[coin] < 0:
                lot_size[coin] = 0

        except:
            pass

        # calculate the volume in coin from QUANTITY in USDT (default)
        volume[coin] = float(QUANTITY / float(last_price[coin]['price']))

        # define the volume with the correct step size
        if coin not in lot_size:
            volume[coin] = float('{:.1f}'.format(volume[coin]))

        else:
            # if lot size has 0 decimal points, make the volume an integer
            if lot_size[coin] == 0:
                volume[coin] = int(volume[coin])
            else:
                volume[coin] = float('{:.{}f}'.format(volume[coin], lot_size[coin]))

    return volume, last_price


def place_buy_orders():
    """Place Buy market orders for each volatile coin found"""
    volume, last_price = convert_volume()
    orders = {}

    for coin in volume:
        ta_result = ta_signal_check(coin, TA_BUY_THRESHOLD)
        if not ta_result:
            print(f'TA signal NOT good, Discard the BUY order {coin}')
            continue

        if coin not in coins_bought:
            print(f"{txcolors.BUY}Preparing to buy {volume[coin]} {coin}{txcolors.DEFAULT}")
            if LOG_TRADES:
                write_log(f"Buy : {volume[coin]} {coin} - {last_price[coin]['price']}")

            # Place the BUY order
            if TEST_MODE:
                orders[coin] = [{'symbol': coin, 'orderId': 0, 'time': datetime.now().timestamp()}]
            else:
                try:
                    client.create_order(symbol=coin, side='BUY', type='MARKET', quantity=volume[coin])
                except Exception as exception:
                    print(f'Place order failed. The reason is: {exception}')
                orders[coin] = wait_for_order_completion(coin)
                print(f'Order placed result: {orders[coin]}')
        else:
            print(f'Signal detected, but there is already an active trade on {coin}.')

    return orders, last_price, volume


def wait_for_order_completion(coin):
    """in PROD mode, we'll get the latest order from history to ensure the order is placed."""
    """Wait for the order to be completed and return the order details."""
    latest_order = client.get_all_orders(symbol=coin, limit=1)

    while not latest_order[coin]:
        print('Binance is being slow in returning the order, calling the API again...')
        latest_order = client.get_all_orders(symbol=coin, limit=1)
        time.sleep(1)

    return latest_order


def sell_coins():
    """sell coins that have reached the STOP LOSS or TAKE a PROFIT threshold"""

    global hsp_head, session_profit

    last_price = get_price(False)  # don't populate a rolling window
    # last_price = get_price(add_to_historical=True) # don't populate a rolling window
    coins_sold = {}

    for coin in list(coins_bought):
        coin_last_price = float(last_price[coin]['price'])
        BuyPrice = float(coins_bought[coin]['bought_at'])
        PriceChange = float((coin_last_price - BuyPrice) / BuyPrice * 100)

        # define stop loss and take profit
        price_take_profit = BuyPrice + (BuyPrice * coins_bought[coin]['take_profit']) / 100
        price_stop_loss = BuyPrice + (BuyPrice * coins_bought[coin]['stop_loss']) / 100

        # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
        if coin_last_price > price_take_profit and USE_TRAILING_STOP_LOSS:

            # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)
            coins_bought[coin]['take_profit'] = PriceChange + TRAILING_TAKE_PROFIT
            coins_bought[coin]['stop_loss'] = coins_bought[coin]['take_profit'] - TRAILING_STOP_LOSS
            if DEBUG:
                print(
                    f"{coin} TP reached {BuyPrice}/{coin_last_price}, change {PriceChange}. adjusting TP {coins_bought[coin]['take_profit']:.2f}  "
                    f"and SL {coins_bought[coin]['stop_loss']:.2f} accordingly to lock-in profit")
            continue

        # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell
        # if this is the case
        if coin_last_price < price_stop_loss or coin_last_price > price_take_profit and not USE_TRAILING_STOP_LOSS:
            coins_sold[coin] = coins_bought[coin]
            profit = place_order_sell(PriceChange, BuyPrice, coin, coin_last_price, coins_sold[coin]['volume'])
            session_profit = session_profit + profit
            continue

        # no action; print once every TIME_DIFFERENCE
        if hsp_head == 1:
            if len(coins_bought) > 0:
                print(
                    f'TP or SL not yet reached, not selling {coin} for now {BuyPrice} - {coin_last_price} : {txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS}{PriceChange - (TRADING_FEE * 2):.2f}% Est:${(QUANTITY * (PriceChange - (TRADING_FEE * 2))) / 100:.2f}{txcolors.DEFAULT}')

    if hsp_head == 1 and len(coins_bought) == 0: print(f'Not holding any coins')

    return coins_sold


def place_order_sell(PriceChange, BuyPrice, coin, coin_latest_price, volume):
    print(f"{txcolors.SELL_PROFIT if PriceChange >= 0. else txcolors.SELL_LOSS}TP or SL reached, "
          f"selling {coins_bought[coin]['volume']} {coin} - {BuyPrice} - {coin_latest_price} : {PriceChange - (TRADING_FEE * 2):.2f}% "
          f"Est:${(QUANTITY * (PriceChange - (TRADING_FEE * 2))) / 100:.2f}{txcolors.DEFAULT}")

    try:
        if LOG_TRADES:
            save_history.update_price(coin, coin_latest_price)
        if not TEST_MODE:
            client.create_order(symbol=coin, side='SELL', type='MARKET', quantity=coins_bought[coin]['volume'])

    # error handling here in case position cannot be placed
    except Exception as e:
        print(e)

    # run the else block if coin has been sold and create a dict for each coin sold
    else:
        # coins_sold[coin] = coins_bought[coin]

        # prevent a system from buying this coin for the next TIME_DIFFERENCE minutes
        volatility_cooloff[coin] = datetime.now()

        # Log trade
        if LOG_TRADES:
            profit = ((coin_latest_price - BuyPrice) * volume) * (
                    1 - (TRADING_FEE * 2))  # adjust for trading fee here
            write_log(
                f"Sell: {volume} {coin} - {BuyPrice} - {coin_latest_price} "
                f"Profit: {profit:.2f} {PriceChange - (TRADING_FEE * 2):.2f}%")
    return PriceChange - (TRADING_FEE * 2)


def update_portfolio(orders, last_price, volume):
    """add every coin bought to our portfolio for tracking/selling later"""
    if DEBUG: print(orders)
    for coin in orders:
        coins_bought[coin] = {
            'symbol': orders[coin][0]['symbol'],
            'orderid': orders[coin][0]['orderId'],
            'timestamp': orders[coin][0]['time'],
            'bought_at': last_price[coin]['price'],
            'volume': volume[coin],
            'stop_loss': -STOP_LOSS,
            'take_profit': TAKE_PROFIT,
        }

        # save to a database
        if LOG_FILE:
            order_log = TradingLog(coins_bought[coin].get('symbol'),
                                   float(coins_bought[coin].get('bought_at')),
                                   0,
                                   coins_bought[coin].get('volume'),
                                   0,
                                   'Buy')
            order_log.order_time = convert_timestamp(coins_bought[coin].get('timestamp'))
            order_log.latest_price = float(coins_bought[coin].get('bought_at'))
            order_log.total = order_log.buy_price * order_log.amount
            order_log.last_update_time = utilities.time_util.now()

            save_history.save_order(order_log)

        # save the coins in a json file in the same directory
        with open(coins_bought_file_path, 'w') as file:
            json.dump(coins_bought, file, indent=4)
        print(f'Order with id {orders[coin][0]["orderId"]} placed and saved to file')


def remove_from_portfolio(coins_sold):
    """Remove coins sold due to SL or TP from portfolio"""
    for coin in coins_sold:
        coins_bought.pop(coin)

    with open(coins_bought_file_path, 'w') as file:
        json.dump(coins_bought, file, indent=4)


def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE, 'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')


def signal_handler(sig, frame):
    global session_profit
    print(f'Receive signal {sig} to quit, sell all coins now')
    last_price = get_price(False)

    for coin in list(coins_bought):
        coin_latest_price = float(last_price[coin]['price'])
        BuyPrice = float(coins_bought[coin]['bought_at'])
        PriceChange = float((coin_latest_price - BuyPrice) / BuyPrice * 100)

        profit = place_order_sell(PriceChange, BuyPrice, coin, coin_latest_price, coins_bought[coin]['volume'])
        session_profit = session_profit + profit

    print(f'Working...Session profit:{session_profit:.2f}% Est:${(QUANTITY * session_profit) / 100:.2f}')
    sys.exit(0)


if __name__ == '__main__':

    # Load arguments then parse settings
    args = parse_args()
    mymodule = {}

    # set to false at Start
    global bot_paused
    bot_paused = False

    DEFAULT_CONFIG_FILE = 'config.yml'
    DEFAULT_CREDS_FILE = 'creds.yml'

    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(config_file)
    parsed_creds = load_config(creds_file)

    # Default no debugging
    # DEBUG = False

    # Load system vars
    TEST_MODE = parsed_config['script_options']['TEST_MODE']
    LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
    LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
    DEBUG_SETTING = parsed_config['script_options'].get('DEBUG')
    AMERICAN_USER = parsed_config['script_options'].get('AMERICAN_USER')

    # Load trading vars
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    QUANTITY = parsed_config['trading_options']['QUANTITY']
    MAX_COINS = parsed_config['trading_options']['MAX_COINS']
    FIATS = parsed_config['trading_options']['FIATS']
    TIME_DIFFERENCE = parsed_config['trading_options']['TIME_DIFFERENCE']
    RECHECK_INTERVAL = parsed_config['trading_options']['RECHECK_INTERVAL']
    CHANGE_IN_PRICE = parsed_config['trading_options']['CHANGE_IN_PRICE']
    STOP_LOSS = parsed_config['trading_options']['STOP_LOSS']
    TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
    CUSTOM_LIST = parsed_config['trading_options']['CUSTOM_LIST']
    TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']
    USE_TRAILING_STOP_LOSS = parsed_config['trading_options']['USE_TRAILING_STOP_LOSS']
    TRAILING_STOP_LOSS = parsed_config['trading_options']['TRAILING_STOP_LOSS']
    TRAILING_TAKE_PROFIT = parsed_config['trading_options']['TRAILING_TAKE_PROFIT']
    TRADING_FEE = parsed_config['trading_options']['TRADING_FEE']
    SIGNALLING_MODULES = parsed_config['trading_options']['SIGNALLING_MODULES']
    TA_BUY_THRESHOLD = parsed_config['trading_options']['TA_BUY_THRESHOLD']
    TA_SELL_THRESHOLD = parsed_config['trading_options']['TA_SELL_THRESHOLD']

    DEBUG = DEBUG_SETTING or args.debug
    # Load creds for correct environment
    access_key, secret_key = load_correct_creds(parsed_creds)

    if DEBUG:
        print(f'loaded config below\n{json.dumps(parsed_config, indent=4)}')
        print(f'Your credentials have been loaded from {creds_file}')

    # Authenticate with the client, Ensure an API key is good before continuing
    if AMERICAN_USER:
        client = BinanceAPIWrapper(access_key, secret_key, tld='us')
    else:
        client = BinanceAPIWrapper(access_key, secret_key)
        if TEST_MODE:
            client.API_URL = 'https://testnet.binance.vision/api'

    # If the users have a bad / incorrect API key.
    # This will stop the script from starting and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
        exit(f'{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}')

    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    if CUSTOM_LIST: tickers = [line.strip() for line in open(TICKERS_LIST)]

    # try to load all the coins bought by the bot if the file exists and is not empty
    coins_bought = {}

    # path to the saved coins_bought file
    coins_bought_file_path = 'coins_bought.json'

    # rolling window of prices; cyclical queue
    HISTORICAL_PRICES = [None] * (TIME_DIFFERENCE * RECHECK_INTERVAL)
    hsp_head = -1

    # prevent including a coin in volatile_coins if it already appeared there less than TIME_DIFFERENCE minutes ago
    volatility_cooloff = {}

    # use separate files for testing and live trading
    if TEST_MODE:
        coins_bought_file_path = 'test_' + coins_bought_file_path

    # if saved coins_bought json file exists, and it's not empty, then load it
    if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size != 0:
        with open(coins_bought_file_path) as file:
            coins_bought = json.load(file)

    if not TEST_MODE:
        if not args.notimeout:  # if no-timeout skips this (fast for dev tests)
            print('WARNING: You are using the Mainnet and live funds. Waiting 30 seconds as a security measure')
            time.sleep(30)

    signals = glob.glob("signals/*.exs")
    for filename in signals:
        for line in open(filename):
            try:
                os.remove(filename)
            except:
                if DEBUG: print(
                    f'{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

    if os.path.isfile("signals/paused.exc"):
        try:
            os.remove("signals/paused.exc")
        except:
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

    # load signalling modules
    try:
        if SIGNALLING_MODULES is not None and len(SIGNALLING_MODULES) > 0:
            for module in SIGNALLING_MODULES:
                print(f'Starting {module}')
                mymodule[module] = importlib.import_module(module)
                t = threading.Thread(target=mymodule[module].do_work, args=())
                t.daemon = True
                t.start()
                time.sleep(2)
        else:
            print(f'No modules to load')
    except Exception as e:
        print(e)

    # seed initial prices
    get_price()
    READ_TIMEOUT_COUNT = 0
    CONNECTION_ERROR_COUNT = 0
    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl-C to stop the script')
    while True:
        try:
            orders, last_price, volume = place_buy_orders()
            update_portfolio(orders, last_price, volume)
            list_coins_sold = sell_coins()
            remove_from_portfolio(list_coins_sold)
        except ReadTimeout as rt:
            READ_TIMEOUT_COUNT += 1
            print(f"{txcolors.WARNING}We got a timeout error from from binance. Going to re-loop. "
                  f"Current Count: {READ_TIMEOUT_COUNT}\n{rt}{txcolors.DEFAULT}")
        except ConnectionError as ce:
            CONNECTION_ERROR_COUNT += 1
            print(f'{txcolors.WARNING}We got a timeout error from from binance. Going to re-loop.'
                  f' Current Count: {CONNECTION_ERROR_COUNT}\n{ce}{txcolors.DEFAULT}')
