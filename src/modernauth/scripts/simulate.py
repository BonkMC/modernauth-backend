import os

import requests, time, random, string
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
SERVER_ID = os.getenv("TEST_SERVER_ID")

SECRET_KEY = os.getenv("TEST_SERVER_CODE")

TOKEN = ''.join(random.choices(string.ascii_letters + string.digits, k=30))
USERNAME = "PyroEdged"

def main():
    headers = {"X-Server-Secret": SECRET_KEY}
    payload = {
        "server_id": SERVER_ID,
        "token": TOKEN,
        "username": USERNAME
    }
    create_token_url = f"{BASE_URL}/api/createtoken"
    resp = requests.post(create_token_url, json=payload, headers=headers)
    if resp.status_code == 200:
        print("Token creation request sent successfully.")
    else:
        print("Failed to create token.")
        return

    print("Open this link in your browser to sign up/login with Auth0:")
    print(f"{BASE_URL}/auth/{SERVER_ID}/{TOKEN}?username={USERNAME}")
    print("Polling the server to see if you're authorized...")

    while True:
        time.sleep(1)
        auth_url = f"{BASE_URL}/api/authstatus/{SERVER_ID}/{TOKEN}"
        resp = requests.get(auth_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("logged_in"):
                print("You are now authorized with the correct Auth0 account!")
                break
        print("Still waiting (not authorized yet)...")

if __name__ == "__main__":
    main()
