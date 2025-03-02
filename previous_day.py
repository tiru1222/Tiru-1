#To get prev day data
import pandas as pd
import requests
from datetime import datetime, timedelta

# Function to get the previous trading day
def get_previous_trading_day(current_date, holidays):
    previous_day = current_date - timedelta(days=1)
    # Adjust for weekends and holidays
    while previous_day.weekday() > 4 or previous_day.strftime('%Y-%m-%d') in holidays:  # 5=Saturday, 6=Sunday
        previous_day -= timedelta(days=1)
    return previous_day

# Fetch or load holiday list
holidays = pd.read_excel('holidays.xlsx', usecols=['date'])['date']

# Get the previous trading day
current_date = datetime.now()
previous_trading_day = get_previous_trading_day(current_date, holidays).strftime('%Y-%m-%d')

# Read the first column data from stock.xlsx (assuming no header)
stock_symbols = pd.read_excel('stock.xlsx', usecols=[0], header=None).iloc[:, 0]

# Clear existing data from 'previous_day_data.xlsx'
prev_data = "previous_day_data.xlsx"
try:
    # Create an empty DataFrame and overwrite the file
    pd.DataFrame(columns=["Stock Name", "Highest Price", "Lowest Price", "Last Price"]).to_excel(prev_data, index=False)
    print(f"Cleared existing data in {prev_data}")
except Exception as e:
    print(f"Error while clearing the file: {e}")

# Prepare a list to store results
results = []
scripts = pd.read_csv('https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz')

# Iterate over each stock symbol
for stock_name in stock_symbols:
    try:
        instrument_key = scripts[scripts['tradingsymbol'] == stock_name]['instrument_key'].values[0]

        url = f'https://api.upstox.com/v2/historical-candle/{instrument_key}/1minute/{previous_trading_day}/{previous_trading_day}'
        headers = {
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers)

        # Check the response status
        if response.status_code == 200:
            # Process the response data
            data = pd.DataFrame.from_dict(response.json()['data']['candles'])
            cols = ['datetime', 'open', 'high', 'low', 'close', 'volume', 'OI']
            data.columns = cols

            # Rename the 'close' column to the stock name
            data = data.rename(columns={'close': stock_name})

            # Select the prices for computation
            prices = data[stock_name]

            # Compute highest, lowest, and last prices
            highest_price = max(prices)
            lowest_price = min(prices)
            last_price = prices.iloc[0]

            # Append the result to the list
            results.append([instrument_key, highest_price, lowest_price, last_price])
        else:
            # If the request fails, log an error
            print(f"Error: {response.status_code} - {response.text} for stock {stock_name}")
    except IndexError:
        print(f"Error: Stock symbol {stock_name} not found in scripts data.")

# Create a DataFrame for the final output
final_data = pd.DataFrame(results, columns=['Instrument_Key', 'Highest Price', 'Lowest Price', 'Last Price'])

# Save the final data to 'previous_day_data.xlsx'
final_data.to_excel(prev_data, index=False)
print(f"Final data saved to {prev_data}")
