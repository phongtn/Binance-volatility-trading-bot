import datetime


class TradingLog:
    def __init__(self, pair, buy_price, sell_price, amount, total, side):
        self.pair = pair
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.filled = amount
        self.total = total
        self.side = side
        self.color = 'pink' if side == 'Buy' else 'green'
        self.order_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
