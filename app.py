import os
import sqlite3
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, redirect, session, url_for, request, jsonify, render_template

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

# Configure Auth0 OAuth
oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)


# Create (or open) the SQLite database for linking Minecraft tokens to Auth0 accounts.
def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS minecraft_links (
         token TEXT PRIMARY KEY,
         auth0_user_id TEXT,
         minecraft_username TEXT,
         auth0_name TEXT,
         email TEXT,
         logged_in INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    if "user" in session:
        user = session["user"]
        name = user.get("userinfo", {}).get("name", "User")
        return f"Logged in as {name}. <a href='{url_for('logout')}'>Logout</a>"
    return "Welcome! <a href='/login'>Log In</a>"


@app.route("/auth/<token>")
def auth_token(token):
    """
    Handles the authentication flow for a Minecraft player using a unique token.
    """
    minecraft_username = request.args.get("username")

    if "user" not in session:
        # Save token (and username, if provided) in session and redirect to login.
        session["minecraft_token"] = token
        if minecraft_username:
            session["minecraft_username"] = minecraft_username
        return redirect(url_for("login"))

    # User is logged in via Auth0.
    user = session["user"]
    auth0_user = user.get("userinfo", {})
    auth0_user_id = auth0_user.get("sub")
    auth0_name = auth0_user.get("name")
    email = auth0_user.get("email")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT auth0_user_id, minecraft_username FROM minecraft_links WHERE token = ?", (token,))
    row = cursor.fetchone()

    if row is None:
        if not minecraft_username:
            conn.close()
            return render_template("error.html", message="Minecraft username is required for sign-up.")

        cursor.execute("""
            INSERT INTO minecraft_links (token, auth0_user_id, minecraft_username, auth0_name, email, logged_in)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (token, auth0_user_id, minecraft_username, auth0_name, email))
        conn.commit()
        conn.close()
        return render_template("success.html",
                               message=f"Account created and linked successfully! You are logged in as {minecraft_username}.")

    else:
        linked_auth0_user_id, linked_minecraft_username = row
        if linked_auth0_user_id == auth0_user_id:
            cursor.execute("UPDATE minecraft_links SET logged_in = 1 WHERE token = ?", (token,))
            conn.commit()
            conn.close()
            return render_template("success.html", message=f"Logged in successfully as {linked_minecraft_username}.")
        else:
            conn.close()
            return render_template("error.html",
                                   message="This Minecraft account is linked with a different Auth0 account.")


@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token_response = oauth.auth0.authorize_access_token()
    session["user"] = token_response

    if "minecraft_token" in session:
        token = session.pop("minecraft_token")
        minecraft_username = session.pop("minecraft_username", None)
        return redirect(url_for("auth_token", token=token, username=minecraft_username))

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    params = {
        "returnTo": url_for("index", _external=True),
        "client_id": os.getenv("AUTH0_CLIENT_ID")
    }
    return redirect(f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?" + urlencode(params, quote_via=quote_plus))


@app.route("/api/authstatus/<token>")
def auth_status(token):
    """
    This API endpoint is polled by the Minecraft plugin to check login status.
    """
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT logged_in FROM minecraft_links WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()

    return jsonify({"logged_in": bool(row and row[0] == 1)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
