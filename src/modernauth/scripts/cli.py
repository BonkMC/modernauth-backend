import click
import os
import secrets
import string
from dotenv import load_dotenv
from modernauth.db.admin_db import AdminDB
from modernauth.db.tokensystem import TokenSystemDB
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
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN)
    config = config_obj.load()
    if server_id in config:
        click.echo(f"Server ID '{server_id}' already exists.")
        return
    secret_key = generate_secret_key(100)
    config[server_id] = {"secret_key": secret_key}
    config_obj.save(config)
    click.echo(f"Added server '{server_id}' with secret key:")
    click.echo(secret_key)

@cli.command("remove-server")
@click.argument("server_id")
def remove_server(server_id):
    """Remove the server with the specified SERVER_ID."""
    config_obj = ServerConfig(mysql_connection=MYSQL_CONN)
    config = config_obj.load()
    if server_id not in config:
        click.echo(f"Server ID '{server_id}' does not exist.")
        return
    del config[server_id]
    config_obj.save(config)
    click.echo(f"Removed server '{server_id}' successfully.")

@cli.command("invite-admin")
@click.argument("email")
def invite_admin(email):
    """Generate an invitation link to add a new admin."""
    token = secrets.token_urlsafe(30)
    token_db = TokenSystemDB(mysql_connection=MYSQL_CONN)
    extra = {"invite_type": "admin", "invite_email": email}
    token_db.create_token(email, token, server_id="invite", ttl=3600, extra_data=extra)
    link = f"{INVITE_BASE_URL}/invite/{token}"
    click.echo("Admin invitation link generated:")
    click.echo(link)

@cli.command("invite-manager")
@click.argument("email")
@click.argument("servers", nargs=-1)
def invite_manager(email, servers):
    """Generate an invitation link for a manager to given SERVERS."""
    token = secrets.token_urlsafe(30)
    token_db = TokenSystemDB(mysql_connection=MYSQL_CONN)
    extra = {"invite_type": "manager", "invite_email": email, "servers": list(servers)}
    token_db.create_token(email, token, server_id="invite", ttl=3600, extra_data=extra)
    link = f"{INVITE_BASE_URL}/invite/{token}"
    click.echo("Manager invitation link generated:")
    click.echo(link)

@cli.command("remove-admin")
@click.argument("email")
def remove_admin_cmd(email):
    """Remove admin privileges for a user with the specified EMAIL."""
    admin_db = AdminDB(mysql_connection=MYSQL_CONN)
    data = admin_db.load()
    removed = False
    for sub, record in list(data.items()):
        if record.get("email") == email and record.get("is_admin"):
            del data[sub]
            removed = True
    admin_db.save(data)
    if removed:
        click.echo(f"Removed admin privileges for '{email}'.")
    else:
        click.echo(f"No admin found with email '{email}'.")

@cli.command("remove-manager")
@click.argument("email")
def remove_manager_cmd(email):
    """Remove manager privileges for a user with the specified EMAIL."""
    admin_db = AdminDB(mysql_connection=MYSQL_CONN)
    data = admin_db.load()
    removed = False
    for sub, record in list(data.items()):
        if record.get("email") == email and not record.get("is_admin"):
            del data[sub]
            removed = True
    admin_db.save(data)
    if removed:
        click.echo(f"Removed manager privileges for '{email}'.")
    else:
        click.echo(f"No manager found with email '{email}'.")

if __name__ == "__main__":
    cli()