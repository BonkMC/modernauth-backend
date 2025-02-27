import os, json, requests
from flask import Flask, redirect, session, url_for, request, render_template, jsonify, send_from_directory
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from urllib.parse import urlencode
from userdb import UserDB
from tokensystem import TokenSystemDB

load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)


def load_server_config():
    """Load the server configuration from disk so that new keys appear without downtime."""
    try:
        with open("server_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# Serve static style.css
@app.route('/style.css')
def serve_style():
    return send_from_directory(os.path.dirname(__file__), 'style.css')


oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)

# Initialize our per-server user and token databases
userdb = UserDB()
tokensdb = TokenSystemDB()


@app.route("/")
def home():
    if "user" in session:
        return render_template("home.html", user=session["user"].get("name"))
    return render_template("home.html", user=None)


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True),
        prompt="login"
    )


@app.route("/callback")
def callback():
    token_response = oauth.auth0.authorize_access_token()
    userinfo = token_response["userinfo"]
    session["user"] = {
        "sub": userinfo["sub"],
        "name": userinfo.get("name"),
        "email": userinfo.get("email")
    }
    # Resume pending authentication if present
    if "incoming_token" in session and "incoming_server_id" in session:
        tk = session.pop("incoming_token")
        server_id = session.pop("incoming_server_id")
        return redirect(url_for("auth_token", server_id=server_id, token=tk))
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    params = {
        "returnTo": url_for("home", _external=True),
        "client_id": os.getenv("AUTH0_CLIENT_ID")
    }
    return redirect(f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?{urlencode(params)}")


# Public authentication endpoint using the public server ID.
@app.route("/auth/<server_id>/<token>")
def auth_token(server_id, token):
    username = request.args.get("username")
    token_data = tokensdb.get_token_data(token)

    # Ensure token (if exists) belongs to the correct server.
    if token_data:
        if token_data.get("server_id") != server_id:
            return render_template("error.html", message="Access Denied.")
    else:
        if not username:
            return render_template("error.html", message="Username required.")
        tokensdb.create_token(username, token, server_id=server_id)

    # If not logged in or session user data is incomplete, store pending info and redirect to login.
    user = session.get("user")
    if not user or "sub" not in user:
        session["incoming_token"] = token
        session["incoming_server_id"] = server_id
        if username:
            session["pending_username"] = username
        return redirect(url_for("login"))

    # Retrieve Auth0 user data.
    sub = user["sub"]
    name = user.get("name")
    email = user.get("email")

    if not username and "pending_username" in session:
        username = session.pop("pending_username")

    # Ensure that the server’s user database exists.
    if server_id not in userdb.data:
        userdb.data[server_id] = {}

    # Sign up new users or log in existing users (scoped by server_id).
    if username not in userdb.data[server_id]:
        userdb.signup(server_id, username, {"sub": sub, "name": name, "email": email})
        tokensdb.authorize_token(token)
        return render_template("success.html", message=f"Created account for {username} on {server_id}.")

    if userdb.login(server_id, username, {"sub": sub, "name": name, "email": email}):
        tokensdb.authorize_token(token)
        return render_template("success.html", message=f"Logged in as {username} on {server_id}.")

    return render_template("error.html", message="Incorrect account. Please logout and try again.")


# Secure API endpoint: The secret key must be provided in the HTTP header.
@app.route("/api/authstatus/<server_id>/<token>", methods=["GET"])
def authstatus(server_id, token):
    # Load the up-to-date server configuration.
    server_config = load_server_config()
    expected_secret = server_config.get(server_id, {}).get("secret_key")
    provided_secret = request.headers.get("X-Server-Secret")
    if not provided_secret or provided_secret != expected_secret:
        return jsonify({"logged_in": False})

    token_data = tokensdb.get_token_data(token)
    if not token_data or token_data.get("server_id") != server_id:
        return jsonify({"logged_in": False})

    username = token_data["username"]
    if (server_id in userdb.data and username in userdb.data[server_id] and
            userdb.data[server_id][username].get("sub") and token_data.get("authorized")):
        tokensdb.remove_token(token)
        return jsonify({"logged_in": True})
    return jsonify({"logged_in": False})


@app.route("/api/isuser/<server_id>/<username>", methods=["GET"])
def isuser(server_id, username):
    if userdb.isuser(server_id, username):
        return jsonify({"exists": True})
    return jsonify({"exists": False})


#########################
# Settings & Account Linking
#########################

@app.route("/settings")
def settings():
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))
    return render_template("settings.html", user=session["user"])


@app.route("/link/<provider>")
def link_provider(provider):
    """
    Initiate linking a new provider (only google is supported) to the current account.
    """
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))

    # Map provider to the corresponding Auth0 connection name.
    connection_map = {
        "google": "google-oauth2"
    }
    if provider not in connection_map:
        return render_template("error.html", message="Unknown provider.")

    # Store the intended linking provider in session.
    session["linking"] = provider
    redirect_uri = url_for("link_callback", provider=provider, _external=True)
    return oauth.auth0.authorize_redirect(
        redirect_uri=redirect_uri,
        connection=connection_map[provider]
    )


def get_management_token():
    """
    Retrieve a Management API token using client credentials.
    Ensure your machine-to-machine application is configured with access to the Auth0 Management API.
    """
    domain = os.getenv("AUTH0_DOMAIN")
    client_id = os.getenv("AUTH0_CLIENT_ID")
    client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    audience = f"https://{domain}/api/v2/"
    url = f"https://{domain}/oauth/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": audience,
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]


@app.route("/link_callback/<provider>")
def link_callback(provider):
    """
    Callback route after the linking provider authentication.
    Uses the Auth0 Management API to link the secondary account with the primary account.
    """
    if "linking" not in session or session["linking"] != provider:
        return render_template("error.html", message="Linking session expired or invalid.")
    session.pop("linking", None)
    try:
        token_response = oauth.auth0.authorize_access_token()
    except Exception as e:
        return render_template("error.html", message="Failed to link account: " + str(e))
    linking_info = token_response.get("userinfo")
    if not linking_info:
        return render_template("error.html", message="No user info returned from linking provider.")

    # Define the connection mapping (must match your Auth0 connection names)
    connection_map = {
        "google": "google-oauth2"
    }
    # Obtain a Management API token.
    try:
        mgmt_token = get_management_token()
    except Exception as e:
        return render_template("error.html", message="Failed to obtain management token: " + str(e))

    primary_user_id = session["user"]["sub"]
    # Extract the secondary account's unique identifier.
    secondary_sub = linking_info["sub"]
    # Remove provider prefix if present (e.g., "google-oauth2|123456789" becomes "123456789")
    secondary_user_id = secondary_sub.split("|")[1] if "|" in secondary_sub else secondary_sub

    payload = {
        "provider": connection_map[provider],
        "user_id": secondary_user_id
    }
    mgmt_url = f"https://{os.getenv('AUTH0_DOMAIN')}/api/v2/users/{primary_user_id}/identities"
    headers = {
        "Authorization": f"Bearer {mgmt_token}",
        "Content-Type": "application/json"
    }
    r = None
    try:
        r = requests.post(mgmt_url, json=payload, headers=headers)
        r.raise_for_status()
    except Exception as e:
        error_details = r.text if r is not None else "No response received"
        return render_template("error.html", message="Error linking account via Management API: " + str(
            e) + " Details: " + error_details)

    # Optionally, update session data to reflect the newly linked account.
    if "linked_accounts" not in session["user"]:
        session["user"]["linked_accounts"] = {}
    session["user"]["linked_accounts"][provider] = linking_info

    message = f"Successfully linked {provider.capitalize()} account."
    return render_template("success.html", message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
