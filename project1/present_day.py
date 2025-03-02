#To get present_day_data.xlsx
import asyncio
import json
import ssl
import websockets
import requests
import pandas as pd
import datetime
from google.protobuf.json_format import MessageToDict
import MarketDataFeedV3_pb2 as pb

EXCEL_FILE = 'present_day_data.xlsx'
INSTRUMENT_KEYS = ["NSE_EQ|INE117A01022", "NSE_EQ|INE931S01010", "NSE_EQ|INE364U01010", "NSE_EQ|INE814H01011", "NSE_EQ|INE079A01024", "NSE_EQ|INE399L01023", "NSE_EQ|INE118A01012", "NSE_EQ|INE028A01039", "NSE_EQ|INE257A01026", "NSE_EQ|INE323A01026", "NSE_EQ|INE476A01022", "NSE_EQ|INE121A01024", "NSE_EQ|INE016A01026", "NSE_EQ|INE361B01024", "NSE_EQ|INE271C01023", "NSE_EQ|INE192R01011", "NSE_EQ|INE129A01019", "NSE_EQ|INE102D01028", "NSE_EQ|INE066F01020", "NSE_EQ|INE176B01034", "NSE_EQ|INE765G01017", "NSE_EQ|INE726G01019", "NSE_EQ|INE646L01027", "NSE_EQ|INE242A01010", "NSE_EQ|INE335Y01020", "NSE_EQ|INE053F01010", "NSE_EQ|INE749A01030", "NSE_EQ|INE758E01017", "NSE_EQ|INE121E01018", "NSE_EQ|INE0J1Y01017", "NSE_EQ|INE670K01029", "NSE_EQ|INE214T01019", "NSE_EQ|INE171A01029", "NSE_EQ|INE663F01024", "NSE_EQ|INE848E01016", "NSE_EQ|INE134E01011", "NSE_EQ|INE318A01026", "NSE_EQ|INE160A01022", "NSE_EQ|INE020B01018", "NSE_EQ|INE092T01019", "NSE_EQ|INE003A01024", "NSE_EQ|INE245A01021", "NSE_EQ|INE685A01028", "NSE_EQ|INE494B01023", "NSE_EQ|INE692A01016", "NSE_EQ|INE854D01024", "NSE_EQ|INE200M01039", "NSE_EQ|INE205A01025", "NSE_EQ|INE758T01015", "NSE_EQ|INE010B01027", "NSE_INDEX|Nifty Next 50"]

# Read the access token from the external file
try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)

def get_market_data_feed_authorize_v3():
    """Get authorization for market data feed."""
    # access_token = 'your_access_token'
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'
    api_response = requests.get(url=url, headers=headers)
    return api_response.json()

def decode_protobuf(buffer):
    """Decode protobuf message."""
    feed_response = pb.FeedResponse()
    feed_response.ParseFromString(buffer)
    return feed_response

def clear_existing_data():
    """Clear existing data in Excel and store instrument keys."""
    df = pd.DataFrame({'Instrument_Key': INSTRUMENT_KEYS, 'LTP_09:15:00': None, 'LTP_09:29:59': None})
    df.to_excel(EXCEL_FILE, index=False)
    print("Existing data cleared, and instrument keys stored.")

async def fetch_market_data():
    """Fetch market data using WebSocket and handle automatic reconnections."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    while True:
        try:
            response = get_market_data_feed_authorize_v3()
            async with websockets.connect(
                response["data"]["authorized_redirect_uri"],
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=40
            ) as websocket:
                print('Connection established')

                await asyncio.sleep(1)
                data = {
                    "guid": "someguid",
                    "method": "sub",
                    "data": {"mode": "ltpc", "instrumentKeys": INSTRUMENT_KEYS}
                }
                binary_data = json.dumps(data).encode('utf-8')
                await websocket.send(binary_data)

                latest_data = {key: None for key in INSTRUMENT_KEYS}
                ltp_110455 = {}
                ltp_110618 = {}

                while True:
                    current_time = datetime.datetime.now().strftime('%H:%M:%S')

                    if current_time < "09:13:10":
                        print("Waiting to start fetching at 09:13:10...")
                        await asyncio.sleep(1)
                        continue

                    if "09:13:40" <= current_time < "09:29:30":
                        print("Paused fetching at 09:13:40. Waiting for 09:29:30 to resume...")
                        await asyncio.sleep(1)
                        continue

                    if current_time >= "09:30:02":
                        print("Stopping fetching at 09:30:02.")
                        break

                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        decoded_data = decode_protobuf(message)
                        data_dict = MessageToDict(decoded_data)

                        if "feeds" in data_dict:
                            for instrument, details in data_dict["feeds"].items():
                                if "ltpc" in details and "ltp" in details["ltpc"]:
                                    latest_data[instrument] = details["ltpc"]["ltp"]
                                    print(f"{instrument}: LTP = {latest_data[instrument]}")

                        if current_time == "09:13:30" and not ltp_110455:
                            ltp_110455 = latest_data.copy()
                            print("Captured LTP at 09:13:30")
                            # Save immediately to ensure data is retained
                            df = pd.read_excel(EXCEL_FILE)
                            df['LTP_09:15:00'] = df['Instrument_Key'].map(ltp_110455)
                            df.to_excel(EXCEL_FILE, index=False)

                        if current_time == "09:29:59" and not ltp_110618:
                            ltp_110618 = latest_data.copy()
                            print("Captured LTP at 09:29:59")

                    except asyncio.TimeoutError:
                        print("No data received, continuing...")
                        continue

                # Ensure both sets of data are saved
                df = pd.read_excel(EXCEL_FILE)

                # Map and save data for 11:06:18
                if ltp_110618:
                    df['LTP_09:29:59'] = df['Instrument_Key'].map(ltp_110618)

                # Save the updated Excel file
                df.to_excel(EXCEL_FILE, index=False)
                print("Data saved to present_day_data.xlsx")

                return  # Exit if fetching completes successfully

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

clear_existing_data()
asyncio.run(fetch_market_data())
