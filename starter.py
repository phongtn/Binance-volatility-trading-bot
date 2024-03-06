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
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta

from binance.enums import *
from binance.exceptions import BinanceAPIException
# Needed for colorful console output
# Installation with: python3 -m pip install colorama (Mac/Linux) or pip install colorama (PC)
from colorama import init
from requests.exceptions import ReadTimeout, ConnectionError

import save_history
import tele_bot
import utilities.time_util
from binance_api_wrapper import BinanceAPIWrapper
from helpers.handle_creds import (
    load_correct_creds, test_api_key
)
from helpers.parameters import (
    parse_args, load_config
)
from repository.trading_log import TradingLog
from tasignal import ta_signal_check
from utilities.make_color import StampedStdout, TxColors
from utilities.time_util import convert_timestamp
import dto.BinanceConverter
from dto.BinanceDto import BinanceTransaction, BinanceTransactionEncoder

init()

# tracks profit/loss each session
global session_profit
session_profit = 0

sys.stdout = StampedStdout(sys.stdout)


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

    global HISTORICAL_PRICES, hsp_head, volatility_cool_off, last_send_tele_mess

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
        wait_next_turn = (timedelta(minutes=float(TIME_DIFFERENCE / RECHECK_INTERVAL)) -
                          (datetime.now() - time_milestone)).total_seconds()
        time.sleep(wait_next_turn)

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

            if coin not in volatility_cool_off:
                volatility_cool_off[coin] = datetime.now() - timedelta(minutes=TIME_DIFFERENCE)

            # only include the coin as volatile if it hasn't been picked up in the last TIME_DIFFERENCE minutes already
            if datetime.now() >= volatility_cool_off[coin] + timedelta(minutes=TIME_DIFFERENCE):
                # disable to include coin continue pump
                volatility_cool_off[coin] = datetime.now()
                volatile_coins[coin] = round(threshold_check, 3)

        elif threshold_check < CHANGE_IN_PRICE:
            coins_down += 1
        else:
            coins_unchanged += 1

    # Disabled until fix
    # print(f'Up: {coins_up} Down: {coins_down} Unchanged: {coins_unchanged}')
    # Here goes new code for external signaling
    externals = external_signals()
    exnumber = 0

    for excoin in externals:
        if excoin not in volatile_coins and excoin not in coins_bought and \
                (len(coins_bought) + exnumber + len(volatile_coins)) < MAX_COINS:
            volatile_coins[excoin] = 1
            exnumber += 1
            print(f'External signal received on {excoin}, calculating volume in {PAIR_WITH}')

    return volatile_coins, HISTORICAL_PRICES[hsp_head]


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
            if DEBUG: print(f'{TxColors.WARNING}Could not remove external signalling file{TxColors.DEFAULT}')

    return external_list


def pause_bot():
    """Pause the script when external indicators detect a bearish trend in the market"""
    global bot_paused, session_profit, hsp_head

    # start counting for how long the bots been paused
    start_time = time.perf_counter()

    while os.path.isfile("signals/paused.exc"):

        if not bot_paused:
            print(f'{TxColors.WARNING}Pausing buying due to change in market conditions, '
                  f'stop loss and take profit will continue to work...{TxColors.DEFAULT}')
            bot_paused = True

        # Sell function needs to work even while paused
        coins_sold = sell_coins()
        remove_from_portfolio(coins_sold)
        get_price(True)

        # pausing here
        if hsp_head == 1: print(f'Working...Session profit: {(session_profit / (QUANTITY * MAX_COINS) * 100):.2f}%'
                                f' Est Profit: ${session_profit:.2f}')
        time.sleep((TIME_DIFFERENCE * 60) / RECHECK_INTERVAL)

    else:
        # stop counting the pause time
        stop_time = time.perf_counter()
        time_elapsed = timedelta(seconds=int(stop_time - start_time))

        # resume the bot and ser pause_bot to False
        if bot_paused:
            print(
                f'{TxColors.WARNING}Resuming buying due to change in market conditions, total sleep time: {time_elapsed}{TxColors.DEFAULT}')
            bot_paused = False

    return


def convert_volume():
    """Sorted the list of volatile coins, Only taking the coin with the highest price change.
    Converts the volume given in QUANTITY from USDT to the coin's volume"""

    volatile_coins, last_price = wait_for_price()
    volume = {}
    if len(volatile_coins) > 0 and len(coins_bought) < MAX_COINS:
        sorted_list = sorted(volatile_coins.items(), key=lambda x: x[1], reverse=True)
        vol_coins = sorted_list[:MAX_COINS - len(coins_bought)]

        for coin, change in vol_coins:
            # Find the correct step size for each coin
            # max accuracy for BTC, for example, is 6 decimal points
            # while XRP is only 1
            vol = float(QUANTITY / float(last_price[coin]['price']))
            volume[coin] = client.round_volume(coin, vol)
    return volume, last_price


def place_buy_orders():
    """Place Buy market orders for each volatile coin found"""
    volume, last_price = convert_volume()
    orders = {}

    for coin in volume:
        if not valid_buy_order(coin):
            continue

        coin_vol = volume[coin]
        coin_latest_price = float(last_price[coin]['price'])
        trans = send_buy_order(coin, coin_vol, coin_latest_price)

        orders[coin] = trans
    return orders, last_price, volume


def send_buy_order(coin: str, coin_vol: float, price: float):
    print(f"{TxColors.BUY}Preparing to buy {coin_vol} {coin}{TxColors.DEFAULT}")
    try:
        if TEST_MODE:
            return BinanceTransaction(symbol=coin, order_id='fake_order', price=price, quantity=coin_vol,
                                      quote_quantity=coin_vol * price, commission=0,
                                      transact_time=datetime.now().timestamp(), side=SIDE_BUY,
                                      status=ORDER_STATUS_FILLED, stop_loss=-STOP_LOSS, take_profit=TAKE_PROFIT)
        else:
            order_result = client.create_order(symbol=coin, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quantity=coin_vol)
            if not order_result:
                order_result = client.get_latest_order(coin)
            trans = dto.BinanceConverter.to_trans(order_result)
            trans.stop_loss = -STOP_LOSS
            trans.take_profit = TAKE_PROFIT
            print(
                f'{TxColors.BUY}Bough {trans.quantity} {trans.symbol} at price: {trans.price}. Total {trans.quote_quantity}')
            return trans
    except Exception as exception:
        print(f'Place order failed. The reason is: {exception}')


def valid_buy_order(coin):
    is_ok = True
    ta_result = ta_signal_check(coin, TA_BUY_THRESHOLD)
    if not ta_result:
        print(f'TA signal NOT good, Discard the BUY order {coin}')
        is_ok = False
    if coin in coins_bought:
        print(f'There is already an active trade on {coin}. No buy more')
        is_ok = False
    if not TEST_MODE and client.check_balance(PAIR_WITH) < QUANTITY:
        print(f'The balance {PAIR_WITH} is insufficient. Discard request BUY {coin}')
        is_ok = False
    return is_ok


def sell_coins():
    """sell coins that have reached the STOP LOSS or TAKE a PROFIT threshold"""
    global hsp_head, session_profit

    last_price = get_price(False)  # don't populate a rolling window
    # last_price = get_price(add_to_historical=True) # don't populate a rolling window
    coins_sold = {}

    for coin, trans in coins_bought.items():
        coin_last_price = float(last_price[coin]['price'])
        BuyPrice = trans.price
        percentile_price_change = float((coin_last_price - BuyPrice) / BuyPrice * 100)
        percentile_price_change = round(percentile_price_change, 3)

        # define stop loss and take profit
        price_take_profit = BuyPrice + (BuyPrice * trans.take_profit) / 100
        price_stop_loss = BuyPrice + (BuyPrice * trans.stop_loss) / 100

        # check that the price is above the take profit and readjust SL and TP accordingly if trialing stop loss used
        if coin_last_price >= price_take_profit and USE_TRAILING_STOP_LOSS:

            # increasing TP by TRAILING_TAKE_PROFIT (essentially next time to readjust SL)
            trans.take_profit = percentile_price_change + TRAILING_TAKE_PROFIT
            trans.stop_loss = trans.take_profit - TRAILING_STOP_LOSS
            if DEBUG:
                print(
                    f"{coin} TP reached {BuyPrice}/{coin_last_price}, Change {percentile_price_change}%. "
                    f"Adjusting TP to {trans.take_profit:.2f}  "
                    f"and SL {trans.stop_loss:.2f} accordingly to lock-in profit")
            continue

        # check that the price is below the stop loss or above take profit
        # (if trailing stop loss not used) and sell if this is the case
        # Todo we should count some cycle price growth up and take profit after 3-5 cycle pump
        if coin_last_price <= price_stop_loss or coin_last_price > price_take_profit and not USE_TRAILING_STOP_LOSS:
            coins_sold[coin] = coins_bought[coin]
            profit = place_order_sell(trans, percentile_price_change, coin_last_price)
            session_profit = session_profit + profit
            continue

        # no action; print once every TIME_DIFFERENCE
        if hsp_head == 1:
            if len(coins_bought) > 0:
                vol = float(trans.quantity)
                est_fee, est_profit = calc_trading_profit(BuyPrice, coin_last_price, vol)
                tx_color = TxColors.SELL_PROFIT if percentile_price_change >= 0. else TxColors.SELL_LOSS
                print(
                    f'TP or SL not yet reached, not selling {coin} for now {BuyPrice}/{coin_last_price}.'
                    f' Change: {tx_color}{percentile_price_change:.2f}%'
                    f" Est profit: ${est_profit:.2f}")

    if hsp_head == 1:
        if len(coins_bought) == 0: print(f'Not holding any coins')
        tmp_message = (f'Working...Session profit: {(session_profit / (QUANTITY * MAX_COINS) * 100):.2f}%'
                       f' Est Profit: ${session_profit:.2f}')
        print(tmp_message)
        if TELE_BOT:
            tele_bot.send(tmp_message)

    return coins_sold


def place_order_sell(trans: BinanceTransaction, price_change: float, coin_latest_price: float):
    coin = trans.symbol
    current_balance = trans.quantity if TEST_MODE else client.check_balance(coin.replace(PAIR_WITH, ''))
    vol = client.round_volume(trans.symbol, current_balance)

    est_fee, est_profit = calc_trading_profit(trans.price, coin_latest_price, vol)
    try:
        if not TEST_MODE:
            sell_result = client.create_order(symbol=coin, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=vol)
            real_fee = 0
            real_price = 0
            for fill_order in sell_result['fills']:
                real_fee += float(fill_order['commission'])
                real_price += float(fill_order['price'])
            est_fee = real_fee
            coin_latest_price = real_price / len(sell_result['fills'])
            est_profit = (coin_latest_price - trans.price) * float(vol) - est_fee

    except Exception as exception:
        print(f'place order error: {exception}')

    # just to make sure the coin sold success
    else:
        # prevent a system from buying this coin for the next TIME_DIFFERENCE minutes
        volatility_cool_off[coin] = datetime.now()

        tx_color = TxColors.SELL_PROFIT if price_change >= 0. else TxColors.SELL_LOSS
        print(f"{tx_color}TP or SL reached, "
              f"selling {vol} {coin} at price: {trans.price}/{coin_latest_price}."
              f" Change: {price_change:.2f}%. Fee: {est_fee:.2f}."
              f" Est profit: ${est_profit:.2f}")

        if LOG_TRADES:
            save_history.update_price(SIDE_SELL, coin, coin_latest_price)
        # Log trade
        if LOG_TRADES:
            write_log(
                f"Sell: {vol} {coin} - {trans.price} - {coin_latest_price} "
                f"Profit: {est_profit:.2f} {price_change:.2f} % ")
    return est_profit


def calc_trading_profit(buy_price, sell_price, vol):
    """double fee for buy and sell"""
    # est_fee = TRADING_FEE / 50 * sell_price * vol
    est_fee = 0
    est_profit = (sell_price - buy_price) * float(vol) - est_fee
    return est_fee, est_profit


def update_portfolio(list_orders: dict):
    """add every coin bought to our portfolio for tracking/selling later"""
    for coin in list_orders:
        trans = list_orders[coin]

        if LOG_TRADES:
            write_log(f"Buy volume: {trans.quantity} {coin} - at price: {trans.price}")
            order_log = TradingLog(coin, trans.price, 0, trans.quantity, trans.quote_quantity, trans.side)
            order_log.order_time = convert_timestamp(trans.transact_time)
            order_log.latest_price = trans.price
            order_log.last_update_time = utilities.time_util.now()
            save_history.update_order(order_log)

        coins_bought[coin] = trans
        save_to_file()
        print(f'Order with id {trans.order_id} placed and saved to file')


def save_to_file():
    with open(coins_bought_file_path, 'w') as coin_bough_file:
        coin_bough_file.write(json.dumps(coins_bought, indent=4, default=lambda o: o.__dict__))


def write_log(logline):
    timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
    with open(LOG_FILE, 'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')


global start_time
time_start_session = datetime.now()


def signal_handler(sig, frame):
    global session_profit
    print(f'Receive signal {sig} to quit, sell all coins now')
    all_coins_price = get_price(False)

    for coin, trans in coins_bought.items():
        coin_latest_price = float(all_coins_price[coin]['price'])
        price_bought = trans.price
        price_change = float((coin_latest_price - price_bought) / price_bought * 100)

        profit = place_order_sell(trans, price_change, coin_latest_price)
        session_profit = session_profit + profit

    # not yet update the log
    time_difference = datetime.now() - time_start_session
    hours, minutes, seconds = utilities.time_util.convert_seconds(time_difference.total_seconds())
    tmp_message = (f'Working...in {hours} h, {minutes} m and {seconds} s. '
                   f'Session profit: {(session_profit / (QUANTITY * MAX_COINS) * 100):.2f}%'
                   f' Est Profit: ${session_profit:.2f}')
    print(tmp_message)
    if TEST_MODE:
        os.remove(coins_bought_file_path)
    sys.exit(0)


def init_config_params(config_file):
    global TEST_MODE, LOG_TRADES, LOG_FILE, TELE_BOT, DEBUG_SETTING, AMERICAN_USER, PAIR_WITH, \
        QUANTITY, MAX_COINS, FIATS, TIME_DIFFERENCE, RECHECK_INTERVAL, CHANGE_IN_PRICE, STOP_LOSS, \
        TAKE_PROFIT, CUSTOM_LIST, TICKERS_LIST, USE_TRAILING_STOP_LOSS, TRAILING_STOP_LOSS, \
        TRAILING_TAKE_PROFIT, TRADING_FEE, SIGNALLING_MODULES, TA_BUY_THRESHOLD
    parsed_config = load_config(config_file)
    # Load system vars
    TEST_MODE = parsed_config['script_options']['TEST_MODE']
    LOG_TRADES = parsed_config['script_options'].get('LOG_TRADES')
    LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
    TELE_BOT = parsed_config['script_options'].get('TELE_BOT')
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

    print(f'loaded config below\n{json.dumps(parsed_config, indent=4)}')
    if TELE_BOT:
        tele_bot.send(f'Start bot success with config {json.dumps(parsed_config, indent=2)}')


def load_modules():
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


def custom_signals():
    signals = glob.glob("signals/*.exs")
    for filename in signals:
        for line in open(filename):
            try:
                os.remove(filename)
            except:
                if DEBUG: print(
                    f'{TxColors.WARNING}Could not remove external signalling file {filename}{TxColors.DEFAULT}')
    if os.path.isfile("signals/paused.exc"):
        try:
            os.remove("signals/paused.exc")
        except:
            if DEBUG: print(f'{TxColors.WARNING}Could not remove external signalling file {filename}{TxColors.DEFAULT}')


def load_exist_coin_bought():
    """ if saved coins_bought json file exists, and it's not empty, then load it """
    existed_coins_bought = {}
    if os.path.isfile(coins_bought_file_path) and os.stat(coins_bought_file_path).st_size != 0:
        with open(coins_bought_file_path) as f:
            existed_coins_bought = json.load(f)
    return existed_coins_bought


def init_binance_client(credentials_file):
    # Load creds for correct environment
    parsed_creds = load_config(credentials_file)
    access_key, secret_key = load_correct_creds(parsed_creds, TEST=TEST_MODE)

    print(f'Your credentials have been loaded from {creds_file}')

    # Authenticate with the client, Ensure an API key is good before continuing
    if AMERICAN_USER:
        client = BinanceAPIWrapper(access_key, secret_key, tld='us')
    else:
        client = BinanceAPIWrapper(access_key, secret_key)
        if TEST_MODE:
            client.API_URL = BinanceAPIWrapper.API_TESTNET_URL
    # If the users have a bad / incorrect API key.
    # This will stop the script from starting and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
        exit(f'{TxColors.SELL_LOSS}{msg}{TxColors.DEFAULT}')
    return client


def remove_from_portfolio(coins_sold):
    """Remove coins sold due to SL or TP from portfolio"""
    for coin in coins_sold:
        coins_bought.pop(coin)
    save_to_file()


if __name__ == '__main__':

    # Load arguments then parse settings
    args = parse_args()
    mymodule = {}

    # set to false at Start
    global bot_paused
    bot_paused = False

    config_file = args.config if args.config else 'config.yml'
    creds_file = args.creds if args.creds else 'creds.yml'

    init_config_params(config_file)
    client = init_binance_client(creds_file)

    DEBUG = DEBUG_SETTING or args.debug
    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    if CUSTOM_LIST: tickers = [line.strip() for line in open(TICKERS_LIST)]

    # path to the saved coins_bought file
    coins_bought_file_path = 'test_coins_bought.json' if TEST_MODE else 'coins_bought.json'

    # try to load all the coins bought by the bot if the file exists and is not empty
    # coins_bought = load_exist_coin_bought()
    coins_bought = {}

    # rolling window of prices; cyclical queue
    HISTORICAL_PRICES = [None] * (TIME_DIFFERENCE * RECHECK_INTERVAL)
    hsp_head = -1

    # prevent including a coin in volatile_coins if it already appeared there less than TIME_DIFFERENCE minutes ago
    volatility_cool_off = {}

    if not TEST_MODE:
        if not args.notimeout:  # if no-timeout skips this (fast for dev tests)
            print('WARNING: You are using the Mainnet and live funds. Waiting 30 seconds as a security measure')
            # time.sleep(30)

    custom_signals()
    load_modules()

    # seed initial prices
    get_price()
    READ_TIMEOUT_COUNT = 0
    CONNECTION_ERROR_COUNT = 0

    signal.signal(signal.SIGINT, signal_handler)
    print('Press Ctrl-C to stop the script')
    while True:
        try:
            orders, last_price, volume = place_buy_orders()
            update_portfolio(orders)
            list_coins_sold = sell_coins()
            remove_from_portfolio(list_coins_sold)
        except ReadTimeout as rt:
            READ_TIMEOUT_COUNT += 1
            print(f"{TxColors.WARNING}We got a timeout error from from binance. Going to re-loop. "
                  f"Current Count: {READ_TIMEOUT_COUNT}\n{rt}{TxColors.DEFAULT}")
        except ConnectionError as ce:
            CONNECTION_ERROR_COUNT += 1
            print(f'{TxColors.WARNING}We got a timeout error from from binance. Going to re-loop.'
                  f' Current Count: {CONNECTION_ERROR_COUNT}\n{ce}{TxColors.DEFAULT}')
