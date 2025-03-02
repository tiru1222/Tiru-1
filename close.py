#To exit all the open positions.
import requests
# Read the access token from the external file
try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)

url = 'https://api.upstox.com/v2/order/positions/exit'
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {access_token}',
}

data = {}

try:
    # Send the POST request
    response = requests.post(url, json=data, headers=headers)

    # Print the response status code and body
    print('Response Code:', response.status_code)
    print('Response Body:', response.json())

except Exception as e:
    # Handle exceptions
    print('Error:', str(e))
