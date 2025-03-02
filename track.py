import asyncio
import json
import ssl
import websockets
import requests
import pandas as pd
import datetime
from google.protobuf.json_format import MessageToDict
import MarketDataFeedV3_pb2 as pb

# Read the access token from the external file
try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)

EXCEL_FILE = 'token_entry.xlsx'

# Function to read instrument keys from Excel
def get_instrument_keys():
    df = pd.read_excel(EXCEL_FILE)
    return df

# Function to authorize market data feed
def get_market_data_feed_authorize_v3():
    # access_token = 'your_access_token'
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'
    api_response = requests.get(url=url, headers=headers)
    return api_response.json()

# Function to cancel an order
def cancel_order(order_id):
    url = f'https://api-hft.upstox.com/v3/order/cancel?order_id={order_id}'
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    response = requests.delete(url, headers=headers)
    print(f'Order {order_id} cancelled:', response.text)

# Function to place a new StopLossMarket order
def place_slm_order(quantity, instrument_token, transaction_type, trigger_price):
    url = 'https://api-hft.upstox.com/v3/order/place'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}',
    }
    data = {
        'quantity': quantity,
        'product': 'I',
        'validity': 'DAY',
        'price': 0,
        'tag': 'SLM_Order',
        'instrument_token': instrument_token,
        'order_type': 'SL-M',
        'transaction_type': transaction_type,
        'disclosed_quantity': 0,
        'trigger_price': trigger_price,
        'is_amo': False,
        'slice': True
    }
    response = requests.post(url, json=data, headers=headers)
    print(f'StopLossMarket order placed for {instrument_token}:', response.json())

async def fetch_market_data():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    while True:
        try:
            df = get_instrument_keys()
            instrument_keys = df['instrument_token'].tolist()
            response = get_market_data_feed_authorize_v3()

            async with websockets.connect(
                response['data']['authorized_redirect_uri'], ssl=ssl_context, ping_interval=20, ping_timeout=40
            ) as websocket:
                print('Connection established')

                data = {'guid': 'someguid', 'method': 'sub', 'data': {'mode': 'ltpc', 'instrumentKeys': instrument_keys}}
                binary_data = json.dumps(data).encode('utf-8')
                await websocket.send(binary_data)

                while True:
                    current_time = datetime.datetime.now().strftime('%H:%M:%S')
                    if current_time >= '14:29:00':
                        print('Stopping data fetching and closing WebSocket connection at 14:29:00')
                        break

                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        decoded_data = pb.FeedResponse()
                        decoded_data.ParseFromString(message)
                        data_dict = MessageToDict(decoded_data)

                        if 'feeds' in data_dict:
                            for instrument, details in data_dict['feeds'].items():
                                if 'ltpc' in details and 'ltp' in details['ltpc']:
                                    ltp = float(details['ltpc']['ltp'])
                                    print(f'{instrument}: LTP = {ltp}')

                                    # Check against token_entry.xlsx
                                    row = df[df['instrument_token'] == instrument]
                                    if not row.empty:
                                        target_price = float(row['target_price'].values[0])
                                        type_value = row['type_value'].values[0]
                                        quantity = int(row['quantity'].values[0])
                                        entry_price = float(row['entry_price'].values[0])
                                        order_id = row['order_id'].values[0]

                                        if (type_value == 'BUY' and ltp <= target_price) or (type_value == 'SELL' and ltp >= target_price):
                                            cancel_order(order_id)
                                            place_slm_order(quantity, instrument, type_value, entry_price)
                                            df = df[df['instrument_token'] != instrument]  # Remove row
                                            df.to_excel(EXCEL_FILE, index=False)
                                            print(f'Updated {EXCEL_FILE}, removed {instrument}')
                                            return  # Restart to use updated instrument keys
                    except asyncio.TimeoutError:
                        print('No data received, continuing...')
                        continue
        except Exception as e:
            print(f'Unexpected error: {e}. Reconnecting in 5 seconds...')
            await asyncio.sleep(5)

asyncio.run(fetch_market_data())
