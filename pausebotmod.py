import os
import threading
import time

from tradingview_ta import TA_Handler, Interval

THRESHOLD = 7  # 7 of 15 MAs indicating sell
TIME_TO_WAIT = 1  # Minutes to wait between analysis
FULL_LOG = False  # List analysis result to console


def analyze():
    analysis = {}
    handler = {}

    handler = TA_Handler(
        symbol='BTCUSDT',
        exchange='BINANCE',
        screener='CRYPTO',
        interval=Interval.INTERVAL_1_MINUTE,
        timeout=10)

    try:
        analysis = handler.get_analysis()
    except Exception as e:
        print(f"pause_bot_mod Exception: {e}")

    ma_sell = analysis.moving_averages['SELL']
    if ma_sell >= THRESHOLD:
        paused = True
        print(
            f'pause_bot_mod: Current threshold {THRESHOLD} The market is NOT looking good, bot paused from buying {analysis.summary}')
    else:
        # print(
        #     f'pause_bot_mod: Current threshold {THRESHOLD} The market is looking GOOD, bot is running {analysis.summary} ')
        paused = False

    return paused


# if __name__ == '__main__':
#     analyze()

def do_work():
    while True:
        if not threading.main_thread().is_alive(): exit()
        # print(f'pause_bot_mod: Fetching market state')
        paused = analyze()
        if paused:
            with open('signals/paused.exc', 'a+') as f:
                f.write('yes')
        else:
            if os.path.isfile("signals/paused.exc"):
                os.remove('signals/paused.exc')

        print(f'pause_bot_mod: Waiting {TIME_TO_WAIT} minutes for next market checkup')
        time.sleep((TIME_TO_WAIT * 60))
