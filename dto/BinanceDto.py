import datetime
from dataclasses import dataclass


@dataclass
class BinanceTransaction:
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
