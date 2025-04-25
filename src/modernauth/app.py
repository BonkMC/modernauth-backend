import os, requests, secrets, string
from flask import Flask, redirect, session, url_for, request, render_template, jsonify, send_from_directory
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from urllib.parse import urlencode
from modernauth.db.userdb import UserDB
from modernauth.db.tokensystem import TokenSystemDB
from modernauth.db.server_config import ServerConfig
import hashlib

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10000 per day"],
    storage_uri="memory://",
)

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DOCS_DIR = os.path.join(BASE_DIR, 'docs', 'build', 'html')

def create_hash(data: str, algorithm: str = 'sha512') -> str:
    """Create a unique hash of a string using the specified algorithm."""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data.encode('utf-8'))
    return hash_obj.hexdigest()

server_config_obj = ServerConfig(
    mysql_connection=os.getenv("MYSQL"),
    hash_function=create_hash
)
userdb = UserDB(
    mysql_connection=os.getenv("MYSQL"),
    hash_function=create_hash
)
tokens_db = TokenSystemDB(
    mysql_connection=os.getenv("MYSQL"),
    hash_function=create_hash
)

@app.route("/developers/")
def developers():
    return redirect('https://docs.bonkmc.org', code=302)


@app.route('/docs/')
def docs_index():
    return redirect('https://docs.bonkmc.org', code=302)


@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'assets'), path)

@app.route("/")
def home():
    if "user" in session:
        return render_template("home.html", user=session["user"].get("name"))
    return render_template("home.html", user=None)


@app.route("/whoweare")
def who_we_are():
    return render_template("whoweare.html")


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


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
        sid = session.pop("incoming_server_id")
        return redirect(url_for("auth_token", server_id=sid, token=tk))
    if "incoming_invite_token" in session:
        tk = session.pop("incoming_invite_token")
        return redirect(url_for("accept_invite", token=tk))
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
    username = request.args.get("username") or session.pop("pending_username", None)
    token_data = tokens_db.get_token_data(token)
    if not token_data or token_data.get("server_id") != server_id:
        return render_template("error.html", message="Invalid token or server mismatch.")
    user = session.get("user")
    if not user or "sub" not in user:
        session["incoming_token"] = token
        session["incoming_server_id"] = server_id
        if username:
            session["pending_username"] = username
        return redirect(url_for("login"))

    sub = user["sub"]

    if not userdb.isuser(server_id, username):
        if userdb.signup(server_id, username, sub):
            tokens_db.authorize_token(token)
            return render_template(
                "success.html",
                message=f"Created account for {username} on {server_id}."
            )
        return render_template("error.html", message="Signup failed.")

    if userdb.login(server_id, username, sub):
        tokens_db.authorize_token(token)
        return render_template(
            "success.html",
            message=f"Logged in as {username} on {server_id}."
        )

    return render_template(
        "error.html",
        message="Auth mismatch. Please logout and try again."
    )


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
    provided_secret = create_hash(request.headers.get("X-Server-Secret"))
    if not provided_secret or provided_secret != expected_secret:
        return jsonify(generic_response), 200
    tokens_db.create_token(username, token, server_id=server_id)
    return jsonify(generic_response), 200


@app.route("/api/authstatus/<server_id>/<token>", methods=["GET"])
def auth_status(server_id, token):
    config = server_config_obj.load()
    expected = config.get(server_id, {}).get("secret_key")
    provided = create_hash(request.headers.get("X-Server-Secret", ""))
    if not expected or provided != expected:
        return jsonify({"logged_in": False})

    token_data = tokens_db.get_token_data(token)
    if not token_data or token_data.get("server_id") != server_id:
        return jsonify({"logged_in": False})

    username = token_data.get("username")
    if userdb.isuser(server_id, username) and token_data.get("authorized"):
        tokens_db.remove_token(token)
        return jsonify({"logged_in": True})

    return jsonify({"logged_in": False})


@app.route("/api/isuser/<server_id>/<username>", methods=["GET"])
def is_user(server_id, username):
    return jsonify({"exists": userdb.isuser(server_id, username)})


@app.route("/settings")
def settings():
    if "user" not in session or "sub" not in session["user"]:
        return redirect(url_for("login"))
    user_sub = session["user"]["sub"]
    return render_template("settings.html", user=session["user"])


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
        return render_template("error.html", message="Error linking account via Management API: " + str(
            e) + " Details: " + error_details)
    if "linked_accounts" not in session["user"]:
        session["user"]["linked_accounts"] = {}
    session["user"]["linked_accounts"][provider] = linking_info
    message = f"Successfully linked {provider.capitalize()} account."
    return render_template("success.html", message=message)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
