import os
import secrets
import string
import sys
from dotenv import load_dotenv
from admin_db import AdminDB
from tokensystem import TokenSystemDB
from server_config import ServerConfig

load_dotenv()

server_config_obj = ServerConfig(mysql_connection=os.getenv("MYSQL"))

# Change the base URL as needed – this is the public URL for invitation acceptance.
INVITE_BASE_URL = "https://modernauth-backend-dev.up.railway.app"


def generate_secret_key(length=100):
    """Generate a random secret key of given length."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def add_server(server_id):
    """Add a new server with the specified server_id."""
    config = server_config_obj.load()
    if server_id in config:
        print(f"Server ID '{server_id}' already exists.")
        return
    secret_key = generate_secret_key(100)
    config[server_id] = {"secret_key": secret_key}
    server_config_obj.save(config)
    print(f"Added server '{server_id}' with secret key:")
    print(secret_key)


def remove_server(server_id):
    """Remove the server with the specified server_id."""
    config = server_config_obj.load()
    if server_id not in config:
        print(f"Server ID '{server_id}' does not exist.")
        return
    del config[server_id]
    server_config_obj.save(config)
    print(f"Removed server '{server_id}' successfully.")


def invite_admin(invite_email):
    """Generate an invitation link to add a new admin (full access)."""
    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(30))
    token_db = TokenSystemDB()
    extra_data = {
        "invite_type": "admin",
        "invite_email": invite_email
    }
    # Use a special server_id "invite" for invitation tokens.
    token_db.create_token(invite_email, token, server_id="invite", ttl=3600, extra_data=extra_data)
    invite_link = f"{INVITE_BASE_URL}/invite/{token}"
    print("Admin invitation link generated:")
    print(invite_link)


def invite_manager(invite_email, servers):
    """Generate an invitation link to add a new server manager (access limited to specified servers)."""
    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(30))
    token_db = TokenSystemDB()
    extra_data = {
        "invite_type": "manager",
        "invite_email": invite_email,
        "servers": servers
    }
    token_db.create_token(invite_email, token, server_id="invite", ttl=3600, extra_data=extra_data)
    invite_link = f"{INVITE_BASE_URL}/invite/{token}"
    print("Manager invitation link generated:")
    print(invite_link)


def remove_admin_cmd(invite_email):
    """Remove admin privileges for a user with the specified email."""
    admin_db = AdminDB()
    data = admin_db.load()
    removed = False
    for user_sub in list(data.keys()):
        record = data[user_sub]
        if record.get("email") == invite_email and record.get("is_admin") is True:
            del data[user_sub]
            removed = True
    admin_db.save(data)
    if removed:
        print(f"Removed admin privileges for user with email '{invite_email}'.")
    else:
        print(f"No admin with email '{invite_email}' found.")


def remove_manager_cmd(invite_email):
    """Remove manager privileges for a user with the specified email."""
    admin_db = AdminDB()
    data = admin_db.load()
    removed = False
    for user_sub in list(data.keys()):
        record = data[user_sub]
        if record.get("email") == invite_email and record.get("is_admin") is False:
            del data[user_sub]
            removed = True
    admin_db.save(data)
    if removed:
        print(f"Removed manager privileges for user with email '{invite_email}'.")
    else:
        print(f"No manager with email '{invite_email}' found.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python controls.py add <server_id>")
        print("  python controls.py remove <server_id>")
        print("  python controls.py invite_admin <email>")
        print("  python controls.py invite_manager <email> <server_id1> [server_id2 ...]")
        print("  python controls.py remove_admin <email>")
        print("  python controls.py remove_manager <email>")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "add":
        if len(sys.argv) != 3:
            print("Usage: python controls.py add <server_id>")
        else:
            add_server(sys.argv[2])
    elif command == "remove":
        if len(sys.argv) != 3:
            print("Usage: python controls.py remove <server_id>")
        else:
            remove_server(sys.argv[2])
    elif command == "invite_admin":
        if len(sys.argv) != 3:
            print("Usage: python controls.py invite_admin <email>")
        else:
            invite_admin(sys.argv[2])
    elif command == "invite_manager":
        if len(sys.argv) < 4:
            print("Usage: python controls.py invite_manager <email> <server_id1> [server_id2 ...]")
        else:
            email = sys.argv[2]
            servers = sys.argv[3:]
            invite_manager(email, servers)
    elif command == "remove_admin":
        if len(sys.argv) != 3:
            print("Usage: python controls.py remove_admin <email>")
        else:
            remove_admin_cmd(sys.argv[2])
    elif command == "remove_manager":
        if len(sys.argv) != 3:
            print("Usage: python controls.py remove_manager <email>")
        else:
            remove_manager_cmd(sys.argv[2])
    else:
        print("Unknown command.")