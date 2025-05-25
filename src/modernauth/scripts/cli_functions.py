import os
import secrets
import string
from dotenv import load_dotenv
from modernauth.app import create_hash
from modernauth.db.server_config import ServerConfig

load_dotenv()

MYSQL_CONN = os.getenv("MYSQL")
INVITE_BASE_URL = os.getenv("BASE_URL")

def generate_secret_key(length=100):
    """Generate a random secret key of given length."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def add_server(server_id):
    """Add a new server with the specified SERVER_ID."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN, hash_function=create_hash)
    config = config_obj.load()
    if server_id in config:
        return False
    secret_key = generate_secret_key(100)
    config[server_id] = {"secret_key": create_hash(secret_key)}
    config_obj.save(config)
    return secret_key


def list_servers():
    """List all servers."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN, hash_function=create_hash)
    config = config_obj.load()
    if not config:
        return False
    return_list = []
    for server_id, server_data in config.items():
        return_list.append(server_id)
    return return_list


def reset_key(server_id):
    """Reset the secret key for the specified SERVER_ID."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN, hash_function=create_hash)
    config = config_obj.load()
    if server_id not in config:
        return False
    secret_key = generate_secret_key(100)
    config[server_id]["secret_key"] = create_hash(secret_key)
    config_obj.save(config)
    return secret_key

def remove_server(server_id):
    """Remove the server with the specified SERVER_ID."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN, hash_function=create_hash)
    config = config_obj.load()
    if server_id not in config:
        return False
    del config[server_id]
    config_obj.save(config)
    return True