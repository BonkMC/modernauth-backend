import os, requests, secrets, string
from flask import Flask, redirect, session, url_for, request, render_template, jsonify, send_from_directory
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from urllib.parse import urlencode
from userdb import UserDB
from tokensystem import TokenSystemDB
from admin_db import AdminDB
from server_config import ServerConfig

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10000 per day"],
    storage_uri="memory://",
)

server_config_obj = ServerConfig(mysql_connection=os.getenv("MYSQL"))

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)

userdb = UserDB(mysql_connection=os.getenv("MYSQL"))
tokensdb = TokenSystemDB(mysql_connection=os.getenv("MYSQL"))
admin_db = AdminDB(mysql_connection=os.getenv("MYSQL"))

@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'assets'), path)

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

@app.route("/developers")
def developers():
    return render_template("developers.html")

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
    if "incoming_token" in session and "incoming_server_id" in session:
        tk = session.pop("incoming_token")
        server_id = session.pop("incoming_server_id")
        return redirect(url_for("auth_token", server_id=server_id, token=tk))
    if "incoming_invite_token" in session:
        token_val = session.pop("incoming_invite_token")
        return redirect(url_for("accept_invite", token=token_val))
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    params = {
        "returnTo": url_for("home", _external=True),
        "client_id": os.getenv("AUTH0_CLIENT_ID")
    }
    return redirect(f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?{urlencode(params)}")

@app.route("/auth/<server_id>/<token>")
def auth_token(server_id, token):
    username = request.args.get("username")
    token_data = tokensdb.get_token_data(token)
    if not token_data:
        return render_template("error.html", message="Invalid token.")
    if token_data.get("server_id") != server_id:
        return render_template("error.html", message="Access Denied.")
    user = session.get("user")
    if not user or "sub" not in user:
        session["incoming_token"] = token
        session["incoming_server_id"] = server_id
        if username:
            session["pending_username"] = username
        return redirect(url_for("login"))
    sub = user["sub"]
    name = user.get("name")
    email = user.get("email")
    if not username and "pending_username" in session:
        username = session.pop("pending_username")
    # Ensure server exists in userdb; if not, add an empty entry.
    data = userdb.load()
    if server_id not in data:
        data[server_id] = {}
        userdb.save(data)
    if username not in data.get(server_id, {}):
        for existing_username, details in data.get(server_id, {}).items():
            if details.get("email") == email:
                return render_template("error.html", message="A user with that email already exists on this server.")
        if userdb.signup(server_id, username, {"sub": sub, "name": name, "email": email}):
            tokensdb.authorize_token(token)
            return render_template("success.html", message=f"Created account for {username} on {server_id}.")
        else:
            return render_template("error.html", message="Signup failed. Possibly duplicate email.")
    if userdb.login(server_id, username, {"sub": sub, "name": name, "email": email}):
        tokensdb.authorize_token(token)
        return render_template("success.html", message=f"Logged in as {username} on {server_id}.")
    return render_template("error.html", message="Incorrect account. Please logout and try again.")

@app.route("/invite/<token>")
def accept_invite(token):
    token_data = tokensdb.get_token_data(token)
    if not token_data or "invite_type" not in token_data:
        return render_template("error.html", message="Invalid or expired invitation token.")
    user = session.get("user")
    if not user or "sub" not in user:
        session["incoming_invite_token"] = token
        return redirect(url_for("login"))
    invite_type = token_data.get("invite_type")
    invite_email = token_data.get("invite_email")
    if invite_type == "admin":
        admin_db.set_admin(user["sub"], True, [], email=invite_email)
        message = "Invitation accepted. You are now an admin with full access."
    elif invite_type == "manager":
        servers = token_data.get("servers", [])
        admin_db.set_admin(user["sub"], False, servers, email=invite_email)
        message = f"Invitation accepted. You now have manager access to servers: {', '.join(servers)}."
    else:
        return render_template("error.html", message="Unknown invitation type.")
    #tokensdb.authorize_token(token)
    tokensdb.remove_token(token)
    return render_template("success.html", message=message)

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
    config = server_config_obj.load()
    expected_secret = config.get(server_id, {}).get("secret_key")
    provided_secret = request.headers.get("X-Server-Secret")
    if not provided_secret or provided_secret != expected_secret:
        return jsonify(generic_response), 200
    tokensdb.create_token(username, token, server_id=server_id)
    return jsonify(generic_response), 200

@app.route("/api/authstatus/<server_id>/<token>", methods=["GET"])
def authstatus(server_id, token):
    config = server_config_obj.load()
    expected_secret = config.get(server_id, {}).get("secret_key")
    provided_secret = request.headers.get("X-Server-Secret")
    if not provided_secret or provided_secret != expected_secret:
        return jsonify({"logged_in": False})
    token_data = tokensdb.get_token_data(token)
    if not token_data or token_data.get("server_id") != server_id:
        return jsonify({"logged_in": False})
    username = token_data["username"]
    if (server_id in userdb.load() and username in userdb.load().get(server_id, {}) and
            userdb.load()[server_id][username].get("sub") and token_data.get("authorized")):
        tokensdb.remove_token(token)
        return jsonify({"logged_in": True})
    return jsonify({"logged_in": False})

@app.route("/api/isuser/<server_id>/<username>", methods=["GET"])
def isuser(server_id, username):
    if userdb.isuser(server_id, username):
        return jsonify({"exists": True})
    return jsonify({"exists": False})

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
        return render_template("error.html", message="Error linking account via Management API: " + str(e) + " Details: " + error_details)
    if "linked_accounts" not in session["user"]:
        session["user"]["linked_accounts"] = {}
    session["user"]["linked_accounts"][provider] = linking_info
    message = f"Successfully linked {provider.capitalize()} account."
    return render_template("success.html", message=message)

@app.route("/admin", methods=["GET"])
def admin_panel():
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))
    user_sub = session["user"]["sub"]
    accessible = admin_db.get_accessible_servers(user_sub)
    if accessible == []:
        return render_template("error.html", message="You do not have admin or manager privileges.")
    # Merge server keys from server config and userdb to cover all servers.
    config = server_config_obj.load()
    user_data = userdb.load()
    all_servers = set(config.keys()) | set(user_data.keys())
    if accessible == "all":
        servers = list(all_servers)
    else:
        servers = [s for s in all_servers if s in accessible]
    selected_server = request.args.get("server_id")
    users = {}
    if selected_server:
        db_data = userdb.load()
        if selected_server in db_data:
            users = db_data[selected_server]
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
    new_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(100))
    config = server_config_obj.load()
    if server_id not in config:
        return jsonify({"error": "Server not found"}), 404
    config[server_id]["secret_key"] = new_code
    server_config_obj.save(config)
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
    db_data = userdb.load()
    if server_id in db_data and username in db_data[server_id]:
        del db_data[server_id][username]
        userdb.save(db_data)
    return redirect(url_for("admin_panel", server_id=server_id))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
