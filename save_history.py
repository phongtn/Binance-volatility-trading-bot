import utilities.time_util
from base_logger import logger
from repository.notion_api import create_page, database_filter, update_page
from repository.trading_log import TradingLog


def update_order(log: TradingLog):
    order_log = find_pair(log.pair)
    if order_log is not None:
        page_properties = convert_order_to_page(log)
        result = update_page(order_log.page_id, page_properties)
        return f"update more volume of coin {log.pair}. Result {result}"
    else:
        return create_new_order(log)


def create_new_order(log: TradingLog):
    page_properties = convert_order_to_page(log)
    page_create_result = create_page(page_properties)
    if page_create_result['object'] == 'page':
        return f"status: Ok. Page ID: {page_create_result['id']}"
    else:
        logger.error(f"create page error {page_create_result['message']}")
        return f"status: {page_create_result['code']}. Message: {page_create_result['message']}"


def convert_page_to_order(pair: str, page_properties: dict):
    buy_price = page_properties['Buy Price'].get('number', 0)
    sell_price = page_properties['Sell Price'].get('number', 0)
    latest_price = page_properties['Latest Price'].get('number', 0)
    amount = page_properties['Amount'].get('number', 0)
    total = page_properties['Total'].get('number', 0)
    side = page_properties['Side']['select']['name']
    order_time = page_properties['Order Time']['date']['start']
    last_update_time = page_properties['Last Update']['date']['start']

    old_order = TradingLog(pair, buy_price, sell_price, amount, total, side)
    old_order.order_time = order_time
    old_order.latest_price = latest_price
    old_order.last_update_time = last_update_time
    return old_order


def convert_order_to_page(log: TradingLog):
    return {
        "Pair": {"title": [{"text": {"content": log.pair}}]},
        "Buy Price": {"number": log.buy_price},
        "Sell Price": {"number": log.sell_price},
        "Total": {"number": log.total},
        "Amount": {"number": log.amount},
        "Side": {"select": {"name": log.side, "color": log.color}},
        "Order Time": {"date": {"start": log.order_time, "end": None}},
        "Last Update": {"date": {"start": log.last_update_time, "end": None}}
    }


def find_pair(pair: str):
    """Find the latest Order by pair"""
    filter_props = {
        "and": [{"property": "Pair", "title": {"equals": pair}},
                {"property": "Side", "select": {"equals": "BUY"}}]
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
        logger.warning('Order Pair "{} not found"'.format(pair))
        return None


def update_price(side: str, pair: str, price: float):
    order_log = find_pair(pair)
    if order_log is not None:
        order_log.sell_price = price
        order_log.side = side
        order_log.color = 'green'
        order_log.last_update_time = utilities.time_util.now()

        page_properties = convert_order_to_page(order_log)
        update_page(order_log.page_id, page_properties)
        logger.debug('update the order to sell')
