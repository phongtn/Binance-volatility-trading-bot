from binance.client import Client


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
