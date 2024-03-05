import datetime
from dataclasses import dataclass
from json import JSONEncoder


@dataclass
class BinanceTransaction():
    order_id: str
    symbol: str
    price: float
    quantity: float
    """Total trading volume"""
    quote_quantity: float
    """trading fee"""
    commission: float
    transact_time: datetime
    side: str
    status: str
    stop_loss: float
    take_profit: float


class BinanceTransactionEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
