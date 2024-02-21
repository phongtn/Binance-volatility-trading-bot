from repository.notion_api import create_page, database_filter
from repository.trading_log import TradingLog


def log_order(log: TradingLog):
    data = {
        "Pair": {"title": [{"text": {"content": log.pair}}]},
        "Buy Price": {"number": log.buy_price},
        "Side": {"select": {"name": log.side, "color": log.color}},
        "Order Time": {"date": {"start": log.order_time, "end": None}}
    }
    page_order = create_page(data)
    if page_order['object'] == 'page':
        return page_order['id'], page_order['properties']
    else:
        return page_order['code'], page_order['message']


def find_pair(pair: str):
    """Find the latest Order by pair"""
    filter_props = {
        "and": [
            {"property": "Pair", "title": {"equals": pair}},
            {"property": "Side", "select": {"equals": "Buy"}}
        ]
    }
    payload = {"filter": filter_props, "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}
    return database_filter(payload)


def update_pair(order: TradingLog):
    pass


if __name__ == '__main__':
    s1 = TradingLog("BTCUSDT", 35.4, 0, 0.0005, 45, "Buy")
    # print(log_order(s1))
    print(find_pair('BTCUSDT'))
