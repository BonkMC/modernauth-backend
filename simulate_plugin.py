import requests, time, random, string, os

BASE_URL = "http://10.1.1.116:3000"  # Adjust as needed
SERVER_ID = "bonk-network"           # Public server ID

# The secret key is stored securely (for example, in environment variables or a secure config)
SECRET_KEY = "FbjToFCI4JNGVPJVHpxoFHiBP4IJWddrwFIH45NP21eEDeolNWIYiacKZVT2CDIdyovQiEPEAEgaGDA87SDisp1oI2a2Jm7cfWox"

TOKEN = ''.join(random.choices(string.ascii_letters + string.digits, k=30))
USERNAME = "PyroEdged"

def main():
    headers = {"X-Server-Secret": SECRET_KEY}
    # Create a token using the new secure API endpoint
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
