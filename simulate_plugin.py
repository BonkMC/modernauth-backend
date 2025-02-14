# simulate_plugin.py
import requests
import time

BASE_URL = "http://127.0.0.1:3000"  # Change if your Flask app is elsewhere
TOKEN = "TestTokenXYZ"
USERNAME = "MyMinecraftUser"

def main():
    print(f"Open this link in your browser to sign up/login with Auth0:")
    print(f"{BASE_URL}/auth/{TOKEN}?username={USERNAME}")
    print("Polling the server to see if you're authorized...")

    while True:
        time.sleep(5)
        resp = requests.get(f"{BASE_URL}/api/authstatus/{TOKEN}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("logged_in"):
                print("You are now authorized with the correct Auth0 account!")
                break
        print("Still waiting (not authorized yet)...")

if __name__ == "__main__":
    main()
