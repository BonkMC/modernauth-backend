import json
import os
import secrets
import string
import sys

CONFIG_FILE = "server_config.json"

def load_config():
    """Load the server configuration from disk."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(config):
    """Save the server configuration to disk."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def generate_secret_key(length=100):
    """Generate a random secret key of given length."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def add_server(server_id):
    """Add a new server with the specified server_id."""
    config = load_config()
    if server_id in config:
        print(f"Server ID '{server_id}' already exists.")
        return
    secret_key = generate_secret_key(100)
    config[server_id] = {"secret_key": secret_key}
    save_config(config)
    print(f"Added server '{server_id}' with secret key:")
    print(secret_key)

def remove_server(server_id):
    """Remove the server with the specified server_id."""
    config = load_config()
    if server_id not in config:
        print(f"Server ID '{server_id}' does not exist.")
        return
    del config[server_id]
    save_config(config)
    print(f"Removed server '{server_id}' successfully.")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        # If only a server_id is provided, default to adding a new server.
        server_id = sys.argv[1]
        add_server(server_id)
    elif len(sys.argv) == 3:
        command = sys.argv[1].lower()
        server_id = sys.argv[2]
        if command == "add":
            add_server(server_id)
        elif command == "remove":
            remove_server(server_id)
        else:
            print("Invalid command. Use 'add' or 'remove'.")
    else:
        print("Usage:")
        print("  To add a server:    python controls.py <server_id>")
        print("  Or:                python controls.py add <server_id>")
        print("  To remove a server: python controls.py remove <server_id>")
