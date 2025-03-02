#To get final_list after filtering and sorting
import pandas as pd
import requests
import math

try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)

# Load the data
prev_day_df = pd.read_excel("previous_day_data.xlsx")
pres_day_df = pd.read_excel("present_day_data.xlsx")

# Merge the data on Instrument_Key
merged_df = prev_day_df.merge(pres_day_df, on="Instrument_Key", how="inner")

# Exclude "NSE_INDEX|Nifty Next 50"
filtered_df = merged_df[merged_df["Instrument_Key"] != "NSE_INDEX|Nifty Next 50"]

# Create lists
sell_list = []
buy_list = []
final_list = []

# Filtering for sell_list
for _, row in filtered_df.iterrows():
    ltp_092959 = row["LTP_09:29:59"]
    lowest_price = row["Lowest Price"]
    last_price = row["Last Price"]

    if (ltp_092959 <= lowest_price) and (last_price * 0.99 <= ltp_092959 <= last_price * 0.994):
        sell_list.append(row["Instrument_Key"])

# Limit to top 10 if needed
sell_list = sell_list[:10]
final_list.extend(sell_list)

# Check condition for NSE_INDEX|Nifty Next 50
nifty_next_50 = merged_df[merged_df["Instrument_Key"] == "NSE_INDEX|Nifty Next 50"]
if sell_list == [] and not nifty_next_50.empty:
    nifty_ltp_092959 = nifty_next_50.iloc[0]["LTP_09:29:59"]
    nifty_last_price = nifty_next_50.iloc[0]["Last Price"]
    nifty_ltp_091500 = nifty_next_50.iloc[0]["LTP_09:15:00"]

    if nifty_ltp_092959 > nifty_last_price and nifty_ltp_092959 > nifty_ltp_091500:
        # Filtering for buy_list
        for _, row in filtered_df.iterrows():
            ltp_092959 = row["LTP_09:29:59"]
            highest_price = row["Highest Price"]
            last_price = row["Last Price"]

            if (ltp_092959 >= highest_price) and (last_price * 1.005 <= ltp_092959 <= last_price * 1.011):
                buy_list.append(row["Instrument_Key"])

        # Limit to top 10 if needed
        buy_list = buy_list[:10]
        final_list.extend(buy_list)

# Output final list
print("Final Instrument Keys:", final_list)

# To place orders for final_list Instrument Keys

url = 'https://api.upstox.com/v2/user/get-funds-and-margin'

headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {access_token}'
}

response = requests.get(url, headers=headers)

print(response.status_code)
response_data = response.json()
capital = response_data['data']['equity']['available_margin']
print(f"The available margin (capital) for equity is: {capital}")

total_len = len(final_list)

# Function to get margin for a single Instrument_Key
def get_margin(instrument_key):
    url = "https://api.upstox.com/v2/charges/margin"
    headers = {
        "accept": "application/json",
        "Authorization": f'Bearer {access_token}',
        "Content-Type": "application/json",
    }
    data = {
        "instruments": [
            {
                "instrument_key": instrument_key,
                "quantity": 1,
                "transaction_type": "BUY",
                "product": "I",
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        return response_data['data']['required_margin']
    else:
        print(f"Error fetching margin for {instrument_key}: {response.text}")
        return None


def place_orders(order_data):
    url = 'https://api.upstox.com/v2/order/multi/place'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
    }
    try:
        response = requests.post(url, json=order_data, headers=headers)
    except Exception as e:
        print("Error:", str(e))

# Prepare order data based on final_list contents
order_data = []

if final_list and final_list == sell_list:  # If final_list contains only sell_list
    transaction_type = "SELL"
elif final_list and final_list == buy_list:  # If final_list contains only buy_list
    transaction_type = "BUY"
else:
    transaction_type = None

if transaction_type:
    for instrument_key in final_list:
        margin = get_margin(instrument_key)
        if margin is not None:
            qty = math.floor((capital / total_len) / margin)
            order_data.append({
                "correlation_id": instrument_key,
                "quantity": qty,
                "product": "I",
                "validity": "DAY",
                "price": 0,
                "tag": f"{transaction_type}_ORDER",
                "instrument_token": instrument_key,
                "order_type": "MARKET",
                "transaction_type": transaction_type,
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False,
                "slice": True,
            })

# Place all orders
if order_data:
    place_orders(order_data)
else:
    print("No orders to place.")
