import time, random, string, json

class TokenSystemDB:
    def __init__(self, filename="data/tokensystem.json"):
        self.filename = filename
        self.data = {}
        self.load()

    def load(self):
        try:
            with open(self.filename, "r") as f:
                self.data = json.load(f)
        except:
            self.data = {}

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f)

    def create_token(self, username, token, ttl=600):
        self.purge_expired_tokens()
        self.data[token] = {
            "username": username,
            "expiration_time": time.time() + ttl,
            "authorized": False
        }
        self.save()
        return token

    def remove_token(self, token):
        if token in self.data:
            del self.data[token]
            self.save()

    def purge_expired_tokens(self):
        now = time.time()
        self.data = {k: v for k, v in self.data.items() if v["expiration_time"] > now}
        self.save()

    def check_token(self, token):
        self.purge_expired_tokens()
        return self.data[token]["username"] if token in self.data else None

    def get_token_data(self, token):
        self.purge_expired_tokens()
        return self.data.get(token, None)

    def authorize_token(self, token):
        self.purge_expired_tokens()
        if token in self.data:
            self.data[token]["authorized"] = True
            self.save()