from repository.notion_api import create_page, database_filter, update_page
from repository.trading_log import TradingLog


def create_order(log: TradingLog):
    page_properties = convert_order_to_page(log)
    page_create_result = create_page(page_properties)
    if page_create_result['object'] == 'page':
        return f"status: Ok. Page ID: {page_create_result['id']}"
    else:
        return f"status: {page_create_result['code']}. Message: {page_create_result['message']}"


def convert_page_to_order(pair: str, page_properties: dict):
    buy_price = page_properties['Buy Price'].get('number', 0)
    sell_price = page_properties['Sell Price'].get('number', 0)
    latest_price = page_properties['Latest Price'].get('number', 0)
    amount = page_properties['Amount'].get('number', 0)
    total = page_properties['Total'].get('number', 0)
    side = page_properties['Side']['select']['name']
    order_time = page_properties['Order Time']['date']['start']

    old_order = TradingLog(pair, buy_price, sell_price, amount, total, side)
    old_order.order_time = order_time
    old_order.latest_price = latest_price
    return old_order


def convert_order_to_page(log: TradingLog):
    return {
        "Pair": {"title": [{"text": {"content": log.pair}}]},
        "Buy Price": {"number": log.buy_price},
        "Sell Price": {"number": log.sell_price},
        "Total": {"number": log.total},
        "Amount": {"number": log.amount},
        "Side": {"select": {"name": log.side, "color": log.color}},
        "Order Time": {"date": {"start": log.order_time, "end": None}}
    }


def find_pair(pair: str):
    """Find the latest Order by pair"""
    filter_props = {
        "and": [{"property": "Pair", "title": {"equals": pair}},
                {"property": "Side", "select": {"equals": "Buy"}}]
    }
    payload = {"page_size": 1, "filter": filter_props,
               "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}
    page_result = database_filter(payload)
    if len(page_result) > 0:
        page_object = page_result[0]
        order = convert_page_to_order(pair, page_object['properties'])
        order.page_id = page_object['id']
        return order
    else:
        return None


def save_order(order: TradingLog):
    order_log = find_pair(order.pair)
    if order_log is None:
        result = create_order(order)
        print(f'create new order: {result}')
    else:
        page_properties = convert_order_to_page(order)
        update_page(order_log.page_id, page_properties)
        print('update the order')
