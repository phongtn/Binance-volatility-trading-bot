class TradingLog:
    def __init__(self, pair: str, buy_price: float, sell_price: float, amount: float, total: float, side: str):
        self.pair = pair
        self.buy_price = buy_price
        self.latest_price = buy_price
        self.sell_price = sell_price
        self.amount = amount
        self.total = total
        self.side = side
        self.color = 'pink' if side == 'BUY' else 'green'
        self.order_time = ''
        self.last_update_time = ''
        self.page_id = ''
