import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Define the file path again (as the code execution state was reset)
file_path = 'BNBUSDT_oneday.csv'

# Load the dataset with the correct delimiter
data = pd.read_csv(file_path)

# Convert the 'date' column to datetime
data['date'] = pd.to_datetime(data['date'])

# Calculations based on user's new request
# Calculate one-minute price volatility based on percent change in closing price
data['price_volatility_pct_change'] = data['close'].pct_change() * 100
data['volume_change'] = data['volume'].diff()


# Relative Strength Index (RSI)
def compute_rsi(data, window):
    delta = data['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)

    ma_up = up.where(delta > 0, 0).rolling(window=window).mean()
    ma_down = down.where(delta < 0, 0).rolling(window=window).mean()

    rs = ma_up / ma_down
    rsi = 100 - (100 / (1 + rs))
    return rsi


# print(data.tail(10))

data['rsi14_manual'] = compute_rsi(data, 14)

# Bollinger Bands
data['bb_mavg_manual'] = data['close'].rolling(window=20).mean()
std_dev = data['close'].rolling(window=20).std()
data['bb_hband_manual'] = data['bb_mavg_manual'] + (std_dev * 2)
data['bb_lband_manual'] = data['bb_mavg_manual'] - (std_dev * 2)

buy_signals = data[
    # (data['close'] <= data['bb_lband_manual']) &
    # (data['rsi14_manual'] < 30)
    # &
    (data['price_volatility_pct_change'] > 0.3)
]

# Process to find profits and losses based on updated criteria
profits_updated = []
stop_losses_updated = []

# Assuming a 24-hour market for minutes in day
minutes_in_day = 24 * 60

# print(data.tail(10))
print(buy_signals[['date', 'close', 'price_volatility_pct_change', 'volume',
                   'volume_change', 'rsi14_manual', 'bb_lband_manual']])

for index, signal in buy_signals.iterrows():
    entry_price = signal['close']
    profit_target = entry_price * 1.04
    stop_loss_target = entry_price * 0.98

    if index + minutes_in_day < len(data):
        look_ahead_window = data.loc[index + 1: index + minutes_in_day]
    else:
        look_ahead_window = data.loc[index + 1:]

    profit_hit = False
    stop_loss_hit = False

    for _, future_data in look_ahead_window.iterrows():
        if future_data['close'] >= profit_target:
            profits_updated.append(profit_target - entry_price)
            profit_hit = True
            print(f'TP at {future_data["date"]} - {future_data["high"]}')
            break
        elif future_data['close'] <= stop_loss_target:
            stop_losses_updated.append(entry_price - stop_loss_target)
            stop_loss_hit = True
            print(f'SL at {future_data["date"]} - {signal["close"]}/{future_data["high"]}')
            break

    if not profit_hit and not stop_loss_hit:
        profits_updated.append(0)

# Calculating outcomes
total_trades_updated = len(profits_updated) + len(stop_losses_updated)
total_profits_updated = sum(profits_updated)
total_losses_updated = sum(stop_losses_updated)
win_rate_updated = len([p for p in profits_updated if p > 0]) / total_trades_updated if total_trades_updated > 0 else 0
average_profit_updated = total_profits_updated / len(profits_updated) if len(profits_updated) > 0 else 0
average_loss_updated = total_losses_updated / len(stop_losses_updated) if len(stop_losses_updated) > 0 else 0

print("==========================================")
print(f'Total Trades Executed: {total_trades_updated}')
print(f'Total Profit from Trades: {total_profits_updated}')
print(f'Total Loss from Trades: {total_losses_updated}')
print(f'Win Rate: {win_rate_updated}')
print(f'Average Profit per Trade: {average_profit_updated}')
print(f'Average Loss per Trade: {average_loss_updated}')
