# tokensystem.py
import time, random, string, json

class TokenSystemDB:
    def __init__(self, filename="tokensystem.json"):
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

    def create_token(self, username, token=None, ttl=600):
        if not token:
            token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        self.purge_expired_tokens()
        self.data[token] = {
            "username": username,
            "expiration_time": time.time() + ttl,
            "authorized": False
        }
        self.save()
        return token

    def purge_expired_tokens(self):
        now = time.time()
        expired = [t for t in self.data if self.data[t]["expiration_time"] < now]
        for t in expired:
            del self.data[t]
        if expired:
            self.save()

    def check_token(self, token):
        self.purge_expired_tokens()
        return self.data[token]["username"] if token in self.data else None

    def get_token_data(self, token):
        self.purge_expired_tokens()
        return self.data.get(token, None)

    def authorize_token(self, token):
        if token in self.data:
            self.data[token]["authorized"] = True
            self.save()