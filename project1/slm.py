import time

# Add a 10-second delay before execution
time.sleep(10)

# Original code (unchanged)
import requests
# Read the access token from the external file
try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)

def get_positions():
    url = 'https://api.upstox.com/v2/portfolio/short-term-positions'
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        print('Error fetching positions:', str(e))
        return []

def place_slm_order(position):
    url = 'https://api-hft.upstox.com/v3/order/place'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    transaction_type = 'BUY' if position['day_buy_quantity'] == 0 else 'SELL'
    trigger_price = (
        position['sell_price'] * 1.0052 if transaction_type == 'BUY' else position['buy_price'] * 0.9948
    )
    quantity = (
        position['day_sell_quantity'] if transaction_type == 'BUY' else position['day_buy_quantity']
    )

    data = {
        "quantity": quantity,
        "product": "I",
        "validity": "DAY",
        "price": 0,
        "tag": "SLM_Order",
        "instrument_token": position['instrument_token'],
        "order_type": "SL-M",
        "transaction_type": transaction_type,
        "disclosed_quantity": 0,
        "trigger_price": round(trigger_price / 0.05) * 0.05,
        "is_amo": False,
        "slice": True
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"Order placed for {position['tradingsymbol']} - Response Code: {response.status_code}")
        print('Response Body:', response.json())
    except Exception as e:
        print(f"Error placing order for {position['tradingsymbol']}: {str(e)}")

def main():
    positions = get_positions()
    if not positions:
        print('No positions found or unable to fetch positions.')
        return

    for position in positions:
        place_slm_order(position)

if __name__ == '__main__':
    main()
