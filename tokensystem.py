import time
import json
import os

class TokenSystemDB:
    def __init__(self, filename="data/tokensystem.json"):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump({}, f)

    def load(self):
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, data):
        with open(self.filename, "w") as f:
            json.dump(data, f)

    def _purge_expired_tokens(self, data):
        now = time.time()
        return {k: v for k, v in data.items() if v.get("expiration_time", 0) > now}

    def create_token(self, username, token, server_id, ttl=600, extra_data=None):
        data = self.load()
        data = self._purge_expired_tokens(data)
        data[token] = {
            "username": username,
            "server_id": server_id,
            "expiration_time": time.time() + ttl,
            "authorized": False
        }
        if extra_data:
            data[token].update(extra_data)
        self.save(data)
        return token

    def remove_token(self, token):
        data = self.load()
        if token in data:
            del data[token]
            self.save(data)

    def purge_expired_tokens(self):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)

    def check_token(self, token):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)
        return data[token]["username"] if token in data else None

    def get_token_data(self, token):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)
        return data.get(token, None)

    def authorize_token(self, token):
        data = self.load()
        data = self._purge_expired_tokens(data)
        if token in data:
            data[token]["authorized"] = True
            self.save(data)
