import os, json, requests, secrets, string
from flask import Flask, redirect, session, url_for, request, render_template, jsonify, send_from_directory
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from urllib.parse import urlencode
from userdb import UserDB
from tokensystem import TokenSystemDB
from admin_db import AdminDB  # New admin database

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

def load_server_config():
    """Load the server configuration from disk so that new keys appear without downtime."""
    try:
        with open("data/server_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Serve static assets
@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'assets'), path)

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
admin_db = AdminDB()  # Initialize admin database

@app.route("/")
def home():
    if "user" in session:
        user_sub = session["user"]["sub"]
        accessible = admin_db.get_accessible_servers(user_sub)
        admin_access = (accessible != [])
        return render_template("home.html", user=session["user"].get("name"), admin_access=admin_access)
    return render_template("home.html", user=None, admin_access=False)

@app.route("/whoweare")
def whoweare():
    return render_template("whoweare.html")

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
    if "incoming_invite_token" in session:
        token = session.pop("incoming_invite_token")
        return redirect(url_for("manager_invite", token=token))
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

    # If token does not exist, do not allow creation – send error page.
    if not token_data:
        return render_template("error.html", message="Invalid token.")

    # Ensure token belongs to the correct server.
    if token_data.get("server_id") != server_id:
        return render_template("error.html", message="Access Denied.")

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

    # Check for duplicate email in new signup.
    if username not in userdb.data[server_id]:
        for existing_username, details in userdb.data[server_id].items():
            if details.get("email") == email:
                return render_template("error.html", message="A user with that email already exists on this server.")
        # Sign up new user.
        if userdb.signup(server_id, username, {"sub": sub, "name": name, "email": email}):
            tokensdb.authorize_token(token)
            return render_template("success.html", message=f"Created account for {username} on {server_id}.")
        else:
            return render_template("error.html", message="Signup failed. Possibly duplicate email.")
    # If user exists, attempt login.
    if userdb.login(server_id, username, {"sub": sub, "name": name, "email": email}):
        tokensdb.authorize_token(token)
        return render_template("success.html", message=f"Logged in as {username} on {server_id}.")
    return render_template("error.html", message="Incorrect account. Please logout and try again.")

# New secure API endpoint for token creation.
@app.route("/api/createtoken", methods=["POST"])
def create_token():
    data = request.get_json()
    generic_response = {"message": "If your token is valid, you will see the appropriate behavior."}
    if not data:
        return jsonify(generic_response), 200
    server_id = data.get("server_id")
    token = data.get("token")
    username = data.get("username")
    if not server_id or not token or not username:
        return jsonify(generic_response), 200

    server_config = load_server_config()
    expected_secret = server_config.get(server_id, {}).get("secret_key")
    provided_secret = request.headers.get("X-Server-Secret")
    if not provided_secret or provided_secret != expected_secret:
        return jsonify(generic_response), 200

    tokensdb.create_token(username, token, server_id=server_id)
    return jsonify(generic_response), 200

# Secure API endpoint: The secret key must be provided in the HTTP header.
@app.route("/api/authstatus/<server_id>/<token>", methods=["GET"])
def authstatus(server_id, token):
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
    user_sub = session["user"]["sub"]
    accessible = admin_db.get_accessible_servers(user_sub)
    admin_access = (accessible != [])
    return render_template("settings.html", user=session["user"], admin_access=admin_access)

@app.route("/link/<provider>")
def link_provider(provider):
    """
    Initiate linking a new provider (only google is supported) to the current account.
    """
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))

    connection_map = {
        "google": "google-oauth2"
    }
    if provider not in connection_map:
        return render_template("error.html", message="Unknown provider.")

    session["linking"] = provider
    redirect_uri = url_for("link_callback", provider=provider, _external=True)
    return oauth.auth0.authorize_redirect(
        redirect_uri=redirect_uri,
        connection=connection_map[provider]
    )

def get_management_token():
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

    connection_map = {
        "google": "google-oauth2"
    }
    try:
        mgmt_token = get_management_token()
    except Exception as e:
        return render_template("error.html", message="Failed to obtain management token: " + str(e))

    primary_user_id = session["user"]["sub"]
    secondary_sub = linking_info["sub"]
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

    if "linked_accounts" not in session["user"]:
        session["user"]["linked_accounts"] = {}
    session["user"]["linked_accounts"][provider] = linking_info

    message = f"Successfully linked {provider.capitalize()} account."
    return render_template("success.html", message=message)

#########################
# Admin Panel Endpoints
#########################

@app.route("/admin", methods=["GET"])
def admin_panel():
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))
    user_sub = session["user"]["sub"]
    accessible = admin_db.get_accessible_servers(user_sub)
    if accessible == []:
        return render_template("error.html", message="You do not have admin or manager privileges.")
    server_config = load_server_config()
    if accessible == "all":
        servers = list(server_config.keys())
    else:
        servers = accessible
    selected_server = request.args.get("server_id")
    users = {}
    if selected_server:
        if selected_server in userdb.data:
            users = userdb.data[selected_server]
    # Determine if current user is a full admin
    is_full_admin = admin_db.is_admin(user_sub)
    return render_template("admin.html", servers=servers, selected_server=selected_server, users=users,
                           is_full_admin=is_full_admin)

@app.route("/admin/reset_code", methods=["POST"])
def reset_code():
    if "user" not in session or "sub" not in session["user"]:
        return jsonify({"error": "Unauthorized"}), 401
    user_sub = session["user"]["sub"]
    accessible = admin_db.get_accessible_servers(user_sub)
    if accessible == []:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    server_id = data.get("server_id")
    if not server_id:
        return jsonify({"error": "Missing server_id"}), 400
    if accessible != "all" and server_id not in accessible:
        return jsonify({"error": "Access denied"}), 403
    # Generate new secret key inline
    new_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(100))
    config = load_server_config()
    if server_id not in config:
        return jsonify({"error": "Server not found"}), 404
    config[server_id]["secret_key"] = new_code
    with open("data/server_config.json", "w") as f:
        json.dump(config, f, indent=4)
    return jsonify({"new_code": new_code})

@app.route("/admin/unregister_user", methods=["POST"])
def unregister_user():
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))
    user_sub = session["user"]["sub"]
    accessible = admin_db.get_accessible_servers(user_sub)
    if accessible == []:
        return render_template("error.html", message="Unauthorized")
    server_id = request.form.get("server_id")
    username = request.form.get("username")
    if not server_id or not username:
        return render_template("error.html", message="Missing parameters.")
    if accessible != "all" and server_id not in accessible:
        return render_template("error.html", message="Access denied.")
    if server_id in userdb.data and username in userdb.data[server_id]:
        del userdb.data[server_id][username]
        userdb.save()
    return redirect(url_for("admin_panel", server_id=server_id))

# New management page for server administration (replacing import users)
@app.route("/admin/manage", methods=["GET", "POST"])
def manage_servers():
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))
    user_sub = session["user"]["sub"]
    if not admin_db.is_admin(user_sub):
        return render_template("error.html", message="Only full admins can access server management.")
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_server":
            server_id = request.form.get("server_id")
            config = load_server_config()
            if server_id in config:
                message = f"Server {server_id} already exists."
            else:
                secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(100))
                config[server_id] = {"secret_key": secret_key}
                with open("data/server_config.json", "w") as f:
                    json.dump(config, f, indent=4)
                message = f"Server {server_id} added successfully with secret key: {secret_key}"
            return render_template("manage_servers.html", message=message, servers=list(config.keys()))
        elif action == "generate_invite":
            server_id = request.form.get("server_id")
            # Generate an invitation token specifically for manager invite.
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(50))
            tokensdb.create_token("manager_invite", token, server_id, ttl=3600)
            invite_link = url_for("manager_invite", token=token, _external=True)
            config = load_server_config()
            message = f"Invitation link generated for server {server_id}."
            return render_template("manage_servers.html", message=message, servers=list(config.keys()), invite_link=invite_link)
        elif action == "add_manager_direct":
            server_id = request.form.get("server_id")
            auth0_id = request.form.get("auth0_id")
            email = request.form.get("email")
            success = admin_db.add_access(auth0_id, email, server_id, is_admin=False)
            if success:
                message = f"Manager access added for {email} on server {server_id}."
            else:
                message = f"Failed to add access. Duplicate email exists for server {server_id}."
            config = load_server_config()
            return render_template("manage_servers.html", message=message, servers=list(config.keys()))
    else:
        config = load_server_config()
        return render_template("manage_servers.html", servers=list(config.keys()))

# New route for manager invitation
@app.route("/manager_invite/<token>")
def manager_invite(token):
    token_data = tokensdb.get_token_data(token)
    if not token_data:
         return render_template("error.html", message="Invalid or expired invitation token.")
    user = session.get("user")
    if not user or "sub" not in user:
         session["incoming_invite_token"] = token
         return redirect(url_for("login"))
    sub = user["sub"]
    email = user.get("email")
    tokensdb.authorize_token(token)
    return render_template("success.html", message=f"Invitation accepted. Your Auth0 ID: {sub}, Email: {email}. Provide this info to your admin for access.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))