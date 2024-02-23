import os
import time

from tradingview_ta import TA_Handler, Interval

MY_EXCHANGE = 'BINANCE'
MY_SCREENER = 'CRYPTO'
MY_FIRST_INTERVAL = Interval.INTERVAL_1_MINUTE
MY_SECOND_INTERVAL = Interval.INTERVAL_5_MINUTES
TA_BUY_THRESHOLD = 18  # How many of the 26 indicators to indicate a buy
PAIR_WITH = 'USDT'
TICKERS = 'signalsample.txt'
TIME_TO_WAIT = 4  # Minutes to wait between analysis
FULL_LOG = False  # List analysis result to console


def analyze(pairs):
    taMax = 0
    taMaxCoin = 'none'
    signal_coins = {}
    first_analysis = {}
    second_analysis = {}
    first_handler = {}
    second_handler = {}
    if os.path.exists('signals/signalsample.exs'):
        os.remove('signals/signalsample.exs')

    for pair in pairs:
        first_handler[pair] = TA_Handler(
            symbol=pair,
            exchange=MY_EXCHANGE,
            screener=MY_SCREENER,
            interval=MY_FIRST_INTERVAL,
            timeout=10
        )
        second_handler[pair] = TA_Handler(
            symbol=pair,
            exchange=MY_EXCHANGE,
            screener=MY_SCREENER,
            interval=MY_SECOND_INTERVAL,
            timeout=10
        )

    for pair in pairs:

        try:
            first_analysis = first_handler[pair].get_analysis()
            second_analysis = second_handler[pair].get_analysis()
        except Exception as e:
            print(f'Exception {pair} : {e}')
            print(f'First handler: {first_handler[pair]}')
            print(f'Second handler: {second_handler[pair]}')
            tacheckS = 0

        first_tacheck = first_analysis.summary['BUY']
        second_tacheck = second_analysis.summary['BUY']
        if FULL_LOG:
            print(f'{pair} First {first_tacheck} Second {second_tacheck}')
        else:
            print(".", end='')

        if first_tacheck > taMax:
            taMax = first_tacheck
            taMaxCoin = pair
        if first_tacheck >= TA_BUY_THRESHOLD and second_tacheck >= TA_BUY_THRESHOLD:
            signal_coins[pair] = pair
            print("")
            print(f'Signal detected on {pair}')
            with open('signals/signalsample.exs', 'a+') as f:
                f.write(pair + '\n')
    print("")
    print(f'Max signal by {taMaxCoin} at {taMax} on shortest timeframe')

    return signal_coins


def ta_signal_check(pair: str, threshold: int, sign_check='BUY'):
    first_handler = TA_Handler(
        symbol=pair,
        exchange=MY_EXCHANGE, screener=MY_SCREENER,
        interval=MY_FIRST_INTERVAL, timeout=10
    )
    second_handler = TA_Handler(
        symbol=pair,
        exchange=MY_EXCHANGE, screener=MY_SCREENER,
        interval=MY_SECOND_INTERVAL, timeout=10
    )

    try:
        first_analysis = first_handler.get_analysis()
        second_analysis = second_handler.get_analysis()
        print(first_analysis.summary)
        print(second_analysis.summary)
        first_ta_result = first_analysis.summary[sign_check]
        second_ta_result = second_analysis.summary[sign_check]
        return first_ta_result >= threshold and second_ta_result >= threshold
    except Exception as e:
        print(f'Exception {pair} : {e}')
        return False


def start_tail():
    signal_coins = {}
    pairs = {}

    pairs = [line.strip() for line in open(TICKERS)]
    for line in open(TICKERS):
        pairs = [line.strip() + PAIR_WITH for line in open(TICKERS)]

    while True:
        print(f'Analyzing {len(pairs)} coins')
        signal_coins = analyze(pairs)
        if len(signal_coins) == 0:
            print(f'No coins above {TA_BUY_THRESHOLD} threshold')
        else:
            print(f'{len(signal_coins)} coins above {TA_BUY_THRESHOLD} threshold on both timeframes')
        print(f'Waiting {TIME_TO_WAIT} minutes for next analysis')
        time.sleep((TIME_TO_WAIT * 60))




# if __name__ == '__main__':
#     print(ta_signal_check("BNBUSDT", 2))
    # start_tail()
