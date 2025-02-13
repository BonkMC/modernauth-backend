'''
Token System designed for the plugin, this is not really useful, but is a possible use.
It is likely much better to simply keep tokens on the server plugin side's memory rather than have this database system.
'''
import os
import time
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

class TokenSystemDB:
    def __init__(self, filename="tokensystem.json"):
        self.data = {}
        self.filename = filename

    def save(self):
        self.purge_expired_tokens()
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def create_token(self, username, token):
        expiration_time = time.time() + 600
        self.data[token] = {"username": username, "expiration_time": expiration_time}
        self.save()
        return True

    def purge_expired_tokens(self):
        for token in list(self.data.keys()):
            if self.data[token]["expiration_time"] < time.time():
                del self.data[token]
        self.save()

    def check_token(self, token):
        if token in self.data:
            if self.data[token]["expiration_time"] > time.time():
                return self.data[token]["username"]
            del self.data[token]
            self.save()
        return None

db = TokenSystemDB()

@app.route('/create_token', methods=['POST'])
def create_token():
    username = request.json['username']
    token = request.json['token']
    if db.create_token(username, token):
        return jsonify({"message": "Token created"})
    return jsonify({"message": "Token creation failed"})

@app.route('/check_token', methods=['POST'])
def check_token():
    token = request.json['token']
    username = db.check_token(token)
    if username:
        return jsonify({"message": "Token valid", "username": username})
    return jsonify({"message": "Token invalid"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3060))
    app.run(host="0.0.0.0", port=port)