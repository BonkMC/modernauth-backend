import os
from flask import Flask, redirect, session, url_for, request, render_template, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from urllib.parse import urlencode
from userdb import UserDB
from tokensystem import TokenSystemDB

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)

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
    session["user"] = {"sub": userinfo["sub"], "name": userinfo.get("name"), "email": userinfo.get("email")}
    if "incoming_token" in session:
        tk = session.pop("incoming_token")
        return redirect(url_for("auth_token", token=tk))
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    params = {
        "returnTo": url_for("home", _external=True),
        "client_id": os.getenv("AUTH0_CLIENT_ID")
    }
    return redirect(f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?{urlencode(params)}")

@app.route("/auth/<token>")
def auth_token(token):
    username = request.args.get("username")
    existing_user = tokensdb.check_token(token)
    if not existing_user:
        if not username:
            return render_template("error.html", message="Username required.")
        # Create token data with authorized=False
        tokensdb.create_token(username, token)
    if "user" not in session:
        session["incoming_token"] = token
        if username:
            session["pending_username"] = username
        return redirect(url_for("login"))
    sub = session["user"]["sub"]
    name = session["user"]["name"]
    email = session["user"]["email"]
    if not username and "pending_username" in session:
        username = session.pop("pending_username")
    if username not in userdb.data:
        # New user -> sign up
        userdb.signup(username, {"sub": sub, "name": name, "email": email})
        # Mark token as authorized
        tokensdb.authorize_token(token)
        return render_template("success.html", message=f"Created account for {username}.")
    # Existing user -> check sub
    if userdb.login(username, {"sub": sub, "name": name, "email": email}):
        tokensdb.authorize_token(token)
        return render_template("success.html", message=f"Logged in as {username}.")
    return render_template("error.html", message="Wrong account.")

@app.route("/api/authstatus/<token>")
def authstatus(token):
    tdata = tokensdb.get_token_data(token)
    if not tdata:
        return jsonify({"logged_in": False})
    username = tdata["username"]
    if username in userdb.data and userdb.data[username].get("sub") and tdata["authorized"]:
        return jsonify({"logged_in": True})
    return jsonify({"logged_in": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))