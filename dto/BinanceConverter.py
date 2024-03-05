from dto.BinanceDto import BinanceTransaction


def to_trans(order_result: dict):
    total = float(order_result.get('cummulativeQuoteQty'))
    fills = order_result['fills']
    fee, price, quantity = 0, 0, 0
    for fill_order in fills:
        fee += float(fill_order['commission'])
        price += float(fill_order['price'])
        quantity += float(fill_order['qty'])
    price = price / len(fills)
    return BinanceTransaction(order_id=order_result.get('orderId'), symbol=order_result.get('symbol'),
                              price=price, quantity=quantity, quote_quantity=total, commission=fee,
                              transact_time=order_result.get('transactTime'), side=order_result.get('side'),
                              status=order_result.get('status'))
