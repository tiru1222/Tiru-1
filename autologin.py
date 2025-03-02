from playwright.sync_api import Playwright, sync_playwright
from urllib.parse import parse_qs,urlparse,quote
import pyotp
import requests
from config import *


rurlEncode = quote(RURL,safe="")

AUTH_URL = f'https://api-v2.upstox.com/login/authorization/dialog?response_type=code&client_id={CLIENT_ID}&redirect_uri={rurlEncode}'


def getAccessToken(code):
    url = 'https://api-v2.upstox.com/login/authorization/token'

    headers = {
        'accept': 'application/json',
        'Api-Version': '2.0',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': SECRET_KEY,
        'redirect_uri': RURL,
        'grant_type': 'authorization_code'
    }

    response = requests.post(url, headers=headers, data=data)
    json_response = response.json()

    # Access the response data
    print(f"access_token:  {json_response['access_token']}")

def run(playwright: Playwright) -> str:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    with page.expect_request(f"*{RURL}?code*") as request:
        page.goto(AUTH_URL)
        page.locator("#mobileNum").click()
        page.locator("#mobileNum").fill(MOBILE_NO)
        page.get_by_role("button", name="Get OTP").click()
        page.locator("#otpNum").click()
        otp = pyotp.TOTP(TOTP_KEY).now()
        page.locator("#otpNum").fill(otp)
        page.get_by_role("button", name="Continue").click()
        page.get_by_label("Enter 6-digit PIN").click()
        page.get_by_label("Enter 6-digit PIN").fill(PIN)
        res = page.get_by_role("button", name="Continue").click()
        page.wait_for_load_state()

    url =    request.value.url
    print(f"Redirect Url with code : {url}")
    parsed = urlparse(url)
    code = parse_qs(parsed.query)['code'][0]
    context.close()
    browser.close()
    return code


with sync_playwright() as playwright:
    code = run(playwright)

url = 'https://api.upstox.com/v2/login/authorization/token'
headers = {
    'accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
}

data = {
    'code': code,
    'client_id': CLIENT_ID,
    'client_secret': SECRET_KEY,
    'redirect_uri': RURL,
    'grant_type': 'authorization_code',
}

response = requests.post(url, headers=headers, data=data)

print(response.status_code)
if response.status_code == 200:
    # Extract the access token from the response
    access_token = response.json()['access_token']
    # Store the access token in a file
    with open("access_token.txt", "w") as token_file:
        token_file.write(access_token)
        print("Access token saved to 'access_token.txt'.")
else:
    print(f"Failed to get access token. Status code: {response.status_code}, Response: {response.text}")

# Read the access token from the external file
try:
    with open("access_token.txt", "r") as token_file:
        access_token = token_file.read().strip()  # Read and remove any extra whitespace
except FileNotFoundError:
    print("Error: 'access_token.txt' file not found. Please ensure the token file exists.")
    exit(1)
