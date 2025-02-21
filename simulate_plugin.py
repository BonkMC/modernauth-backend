import requests, time, random, string, os

BASE_URL = "http://127.0.0.1:3000"  # Adjust as needed
SERVER_ID = "bonk-network"           # Public server ID

# The secret key is stored securely (for example, in environment variables or a secure config)
SECRET_KEY = "VYvcvj1gbCdFwo9VoWtKRQRsnaLccWDRzvtAkt47jgxdJRLMsSMR8UkKjjbJAdHl75CH4LO8086OcC7yuKPjkCYqTdLec51zXjL"

TOKEN = ''.join(random.choices(string.ascii_letters + string.digits, k=30))
USERNAME = "MyMinecraftUser"

def main():
    print("Open this link in your browser to sign up/login with Auth0:")
    print(f"{BASE_URL}/auth/{SERVER_ID}/{TOKEN}?username={USERNAME}")
    print("Polling the server to see if you're authorized...")

    headers = {"X-Server-Secret": SECRET_KEY}
    while True:
        time.sleep(1)
        resp = requests.get(f"{BASE_URL}/api/authstatus/{SERVER_ID}/{TOKEN}", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("logged_in"):
                print("You are now authorized with the correct Auth0 account!")
                break
        print("Still waiting (not authorized yet)...")

if __name__ == "__main__":
    main()
