import click
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

@click.group()
def cli():
    """ModernAuth administration commands."""
    pass

@cli.command("add-server")
@click.argument("server_id")
def add_server(server_id):
    """Add a new server with the specified SERVER_ID."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN, hash_function=create_hash)
    config = config_obj.load()
    if server_id in config:
        click.echo(f"Server ID '{server_id}' already exists.")
        return
    secret_key = generate_secret_key(100)
    config[server_id] = {"secret_key": create_hash(secret_key)}
    config_obj.save(config)
    click.echo(f"Added server '{server_id}' with secret key:")
    click.echo(secret_key)

@cli.command("remove-server")
@click.argument("server_id")
def remove_server(server_id):
    """Remove the server with the specified SERVER_ID."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN, hash_function=create_hash)
    config = config_obj.load()
    if server_id not in config:
        click.echo(f"Server ID '{server_id}' does not exist.")
        return
    del config[server_id]
    config_obj.save(config)
    click.echo(f"Removed server '{server_id}' successfully.")


if __name__ == "__main__":
    cli()