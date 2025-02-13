import os
import flask
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

class UserDB:
    def __init__(self, filename="database.json"):
        self.data = {}
        self.filename = filename

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def signup(self, username, auth0_feedback):
        if username not in self.data:
            self.data[username] = auth0_feedback
            self.save()
            return True
        return False

    def login(self, username, auth0_feedback):
        if username in self.data and self.data[username] == auth0_feedback:
            return True
        return False

db = UserDB()

@app.route('/signup', methods=['POST'])
def signup():
    username = request.json['username']
    auth0_feedback = request.json['auth0_feedback']
    if db.signup(username, auth0_feedback):
        return jsonify({"message": "Signup successful"})
    return jsonify({"message": "Signup failed"})

@app.route('/login', methods=['POST'])
def login():
    username = request.json['username']
    auth0_feedback = request.json['auth0_feedback']
    if db.login(username, auth0_feedback):
        return jsonify({"message": "Login successful"})
    return jsonify({"message": "Login failed"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3030))
    app.run(host="0.0.0.0", port=port)