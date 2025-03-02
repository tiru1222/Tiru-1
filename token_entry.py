import requests
import pandas as pd

# Read the access token from the external file
try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)
# Define file name
file_name = "token_entry.xlsx"

# Step 1: Clear existing data from token_entry.xlsx
columns = ["instrument_token", "quantity", "entry_price", "type_value", "target_price", "order_id"]
df = pd.DataFrame(columns=columns)
df.to_excel(file_name, index=False)

# Step 2: Fetch current positions
def fetch_positions():
    url = 'https://api.upstox.com/v2/portfolio/short-term-positions'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("Error fetching positions:", response.text)
        return []

positions = fetch_positions()

# Filter positions where either buy_price or sell_price is 0.0
filtered_positions = [p for p in positions if p.get("buy_price", 0.0) == 0.0 or p.get("sell_price", 0.0) == 0.0]

# Prepare data for token_entry.xlsx
entry_data = []
for position in filtered_positions:
    instrument_token = position.get("instrument_token", "")
    quantity = position.get("quantity", 0)
    entry_price = position.get("sell_price", 0.0) if position.get("buy_price", 0.0) == 0.0 else position.get("buy_price", 0.0)
    type_value = "BUY" if position.get("buy_price", 0.0) == 0.0 else "SELL"
    target_price = (entry_price * 0.991) if type_value == "BUY" else (entry_price * 1.009)

    entry_data.append([instrument_token, quantity, entry_price, type_value, target_price, None])

# Save to token_entry.xlsx
df = pd.DataFrame(entry_data, columns=columns)
df.to_excel(file_name, index=False)

# Step 3: Fetch orders
def fetch_orders():
    url = 'https://api.upstox.com/v2/order/retrieve-all'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("Error fetching orders:", response.text)
        return []

orders = fetch_orders()
instrument_tokens = df["instrument_token"].tolist()

# Identify valid orders
valid_orders = {order.get("instrument_token", ""): order.get("order_id", None) for order in orders
                if order.get("instrument_token", "") in instrument_tokens and order.get("status", "") not in ['rejected', 'cancelled', 'complete']}

# Update order_id column in token_entry.xlsx
df["order_id"] = df["instrument_token"].map(valid_orders)
df.to_excel(file_name, index=False)

print("token_entry.xlsx updated successfully!")
