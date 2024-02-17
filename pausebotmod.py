from tradingview_ta import TA_Handler, Interval, Exchange
import os
import time
import threading

INTERVAL = Interval.INTERVAL_1_MINUTE  # Timeframe for analysis

EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'
SYMBOL = 'BTCUSDT'
THRESHOLD = 7  # 7 of 15 MAs indicating sell
TIME_TO_WAIT = 1  # Minutes to wait between analysis
FULL_LOG = False  # List analysis result to console


def analyze():
    analysis = {}
    handler = {}

    handler = TA_Handler(
        symbol=SYMBOL,
        exchange=EXCHANGE,
        screener=SCREENER,
        interval=INTERVAL,
        timeout=10)

    try:
        analysis = handler.get_analysis()
    except Exception as e:
        print("pausebotmod:")
        print("Exception:")
        print(e)

    ma_sell = analysis.moving_averages['SELL']
    if ma_sell >= THRESHOLD:
        paused = True
        print(f'pause_bot_mod: Market not looking too good, bot paused from buying {ma_sell}/{THRESHOLD} '
              f'Waiting {TIME_TO_WAIT} minutes for next market checkup')
    else:
        print(f'pause_bot_mod: Market looks ok, bot is running {ma_sell}/{THRESHOLD} '
              f'Waiting {TIME_TO_WAIT} minutes for next market checkup ')
        paused = False

    return paused


# if __name__ == '__main__':
def do_work():
    while True:
        if not threading.main_thread().is_alive(): exit()
        print(f'pause_bot_mod: Fetching market state')
        paused = analyze()
        if paused:
            with open('signals/paused.exc', 'a+') as f:
                f.write('yes')
        else:
            if os.path.isfile("signals/paused.exc"):
                os.remove('signals/paused.exc')

        print(f'pause_bot_mod: Waiting {TIME_TO_WAIT} minutes for next market checkup')
        time.sleep((TIME_TO_WAIT * 60))
