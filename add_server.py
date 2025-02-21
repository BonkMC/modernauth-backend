import json, os, secrets, string, sys

CONFIG_FILE = "server_config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def generate_secret_key(length=100):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def add_server(server_id):
    config = load_config()
    if server_id in config:
        print(f"Server ID '{server_id}' already exists.")
        return
    secret_key = generate_secret_key(100)
    config[server_id] = {"secret_key": secret_key}
    save_config(config)
    print(f"Added server '{server_id}' with secret key:")
    print(secret_key)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_server.py <server_id>")
        sys.exit(1)
    server_id = sys.argv[1]
    add_server(server_id)
