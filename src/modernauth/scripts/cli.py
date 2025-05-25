import click
import os
import secrets
import string
from dotenv import load_dotenv
from modernauth.app import create_hash
from modernauth.db.server_config import ServerConfig
import modernauth.scripts.cli_functions as cf
from modernauth.scripts.cli_functions import MYSQL_CONN, INVITE_BASE_URL

load_dotenv()

MYSQL_CONN = os.getenv("MYSQL")
INVITE_BASE_URL = os.getenv("BASE_URL")

@click.group()
def cli():
    """ModernAuth administration commands."""
    pass

@cli.command("add-server")
@click.argument("server_id")
def add_server(server_id):
    response = cf.add_server(server_id)
    if not response:
        click.echo(f"Server ID '{server_id}' already exists.")
        return
    click.echo(f"Added server '{server_id}' with secret key:")
    click.echo(response)

@cli.command("list-servers")
def list_servers():
    response = cf.list_servers()
    if not response:
        click.echo("No servers found.")
        return
    for server_id in response:
        click.echo(f"Server ID: {server_id}")

@cli.command("reset-key")
@click.argument("server_id")
def reset_key(server_id):
    response = cf.reset_key(server_id)
    if not response:
        click.echo(f"Server ID '{server_id}' does not exist.")
        return
    click.echo(f"Reset secret key for server '{server_id}':")
    click.echo(response)

@cli.command("remove-server")
@click.argument("server_id")
def remove_server(server_id):
    response = cf.remove_server(server_id)
    if not response:
        click.echo(f"Server ID '{server_id}' does not exist.")
        return
    click.echo(f"Removed server '{server_id}' successfully.")


if __name__ == "__main__":
    cli()