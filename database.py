# Write a api based database: with flask without using sqlite3, using json to store data

import os
import flask
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

class Database:
    def __init__(self):
        self.data = {}

    def signup(self, username, auth0_feedback):
        if username not in self.data:
            self.data[username] = auth0_feedback
            return True
        return False

    def login(self, username, auth0_feedback):
        if username in self.data and self.data[username] == auth0_feedback:
            return True
        return False

db = Database()

#create flask api post gets for signing up and logiging in
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