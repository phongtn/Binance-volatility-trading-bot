from datetime import timedelta, datetime

from binance.client import Client
from binance.helpers import round_step_size


class BinanceAPIWrapper(Client):
    def rolling_window_price_change(self, pair: str, window: str):
        """
        Rolling window price change statistics. Note: This endpoint is different from the GET /api/v3/ticker/24hr
        endpoint. The window used to compute statistics will be no more than 59999ms from the requested windowSize.
        openTime for /api/v3/ticker always starts in a minute, while the closeTime is the current time of the
        request. As such, the effective window will be up to 59999ms wider than windowSize.
        E.g. If the closeTime is 1641287867099 (January 04, 2022 09:17:47:099 UTC),
        and the windowSize is 1d the openTime will be: 1641201420000 (January 3, 2022, 09:17:00 UTC)
        https://binance-docs.github.io/apidocs/spot/en/#rolling-window-price-change-statistics
        """
        params = {
            'symbol': pair,
            'windowSize': window
        }
        return self._get('ticker', data=params, version=self.PRIVATE_API_VERSION)

    def check_balance(self, symbol: str):
        try:
            balance = self.get_asset_balance(asset=symbol)
            free = balance.get('free')
            return float(free)
        except Exception as exception:
            print(f'get account balance failed. The reason is: {exception}')

    def round_volume(self, symbol: str, vol):
        try:
            info = self.get_symbol_info(symbol)
            step_size = info['filters'][1]['stepSize']
            return round_step_size(vol, step_size)
        except Exception as exception:
            print(f'round volume failed: {exception}')

    def round_price(self, symbol: str, price):
        try:
            info = self.get_symbol_info(symbol)
            tick_size = info['filters'][0]['tickSize']
            return round_step_size(price, tick_size)
        except Exception as exception:
            print(f'round price failed: {exception}')

    def get_klines_minutes(self, symbol: str, interval: str, duration: int):
        end = datetime.now()
        start = (end - timedelta(minutes=float(duration))).timestamp()
        return self.get_klines(symbol=symbol, interval=interval, startTime=int(start * 1000),
                               endTime=int(end.timestamp() * 1000), timeZone=0)

    def top_price_change_24h(self, limit: int):
        all_ticker = self.get_ticker()
        cleaned_list = [item for item in all_ticker if 'USDT' in item.get('symbol', '')]
        sorted_list = sorted(cleaned_list, key=lambda x: float(x['priceChangePercent']), reverse=True)
        return sorted_list[:limit]


