import pandas as pd
from pandas import DataFrame
from data.tech_analysis import TechAnalysis


def init_data(raw_data):
    for line in raw_data:
        del line[6:]
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    df = pd.DataFrame(raw_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'], unit='ms')
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df['price_pct_change'] = df['close'].pct_change() * 100
    df['volume_change'] = df['volume'].diff()
    # print(df.tail(5))
    return df


# Relative Strength Index (RSI)
def compute_bollinger_bands(df, window: int = 20):
    # Bollinger Bands
    df['bb_mavg_manual'] = df['close'].rolling(window=window).mean()
    std_dev = df['close'].rolling(window=window).std()
    df['bb_hband_manual'] = df['bb_mavg_manual'] + (std_dev * 2)
    df['bb_lband_manual'] = df['bb_mavg_manual'] - (std_dev * 2)
    return df


def count_consecutive_sequences(arr: []):
    positive_count = 0
    negative_count = 0

    for num in arr:
        if num > 0:
            positive_count += 1
        elif num <= 0:
            negative_count += 1

    return positive_count, negative_count

def append_row(df, row):
    return pd.concat([
                df,
                pd.DataFrame([row], columns=row.index)]
           ).reset_index(drop=True)

def back_testing(raw_data: DataFrame):
    data = init_data(raw_data)
    TA = TechAnalysis()
    data = TA.calculate_technicals(data)

    data['rsi_pct_change'] = data['RSI14'].pct_change() * 100

    # print(data[['date', 'close', 'price_pct_change', 'RSI14', 'rsi_pct_change', 'EMA']])
    data.to_csv(f'data/result_3m_oneday.csv', sep='\t', encoding='utf-8')

    # Identify the buy signal
    # buy_signals = data[
    #     # (data['close'] <= data['bb_lband_manual']) &
    #     # (data['RSI14'] < 50)
    #     # &
    #     (data['price_pct_change'] > 0.3)
    # ]
    buy_signals = pd.DataFrame()

    for index, rows in data.iterrows():
        if rows['price_pct_change'] > 0.3:
            rsi_con = data['rsi_pct_change'][index - 2: index].to_numpy()
            # print(f'{rsi_con} : {rows["date"]}')
            # print("===============")
            pos_count, neg_count = count_consecutive_sequences(rsi_con)

            if pos_count >= 2:
                buy_signals = append_row(buy_signals, rows)

    # Process to find profits and losses based on updated criteria
    profits_updated = []
    stop_losses_updated = []

    # Assuming a 24-hour market for minutes in the day
    minutes_in_day = 24 * 60

    print(buy_signals.head(10))

    for index, signal in buy_signals.iterrows():
        entry_price = signal['close']  # buy at close price
        profit_target = entry_price * 1.02
        stop_loss_target = entry_price * 0.98

        if index + minutes_in_day < len(data):
            look_ahead_window = data.loc[index + 1: index + minutes_in_day]
        else:
            look_ahead_window = data.loc[index + 1:]

        profit_hit = False
        stop_loss_hit = False

        for _, future_data in look_ahead_window.iterrows():
            if future_data['high'] >= profit_target:
                profits_updated.append(future_data['high'] - entry_price)
                profit_hit = True
                # print(f'TP at {future_data["date"]} - {future_data["high"]}')
                break
            elif future_data['low'] <= stop_loss_target:
                stop_losses_updated.append(entry_price - future_data['low'])
                stop_loss_hit = True
                # print(f'SL at {future_data["date"]} - {signal["close"]}/{future_data["high"]}')
                break

        if not profit_hit and not stop_loss_hit:
            profits_updated.append(0)

    # Calculating outcomes
    total_trades_updated = len(profits_updated) + len(stop_losses_updated)
    total_profits_updated = sum(profits_updated)
    total_losses_updated = sum(stop_losses_updated)
    asset_remaining = total_profits_updated - total_losses_updated
    win_rate_updated = len(
        [p for p in profits_updated if p > 0]) / total_trades_updated if total_trades_updated > 0 else 0
    average_profit_updated = total_profits_updated / len(profits_updated) if len(profits_updated) > 0 else 0
    average_loss_updated = total_losses_updated / len(stop_losses_updated) if len(stop_losses_updated) > 0 else 0

    # print(
    #     f'Total Trades Executed: {total_trades_updated}. '
    #     f'Total Profits/Losses: {len(profits_updated)}/{len(stop_losses_updated)}')
    # print(f'Total Profit from Trades: {total_profits_updated:.3f}')
    # print(f'Total Loss from Trades: {total_losses_updated:.3f}')
    # print(f'Profit/Loss: {asset_remaining:.3f}')
    # print(f'Win Rate: {round(win_rate_updated * 100, 3)}')
    # print(f'Average Profit per Trade: {average_profit_updated:.3f}')
    # print(f'Average Loss per Trade: {average_loss_updated:.3f}')

    return total_trades_updated, total_profits_updated, total_losses_updated, asset_remaining, win_rate_updated
