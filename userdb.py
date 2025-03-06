import json
import os

class UserDB:
    def __init__(self, filename="data/database.json"):
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
            json.dump(data, f, indent=4)

    def isuser(self, server_id, username):
        data = self.load()
        return server_id in data and username in data[server_id]

    def signup(self, server_id, username, authdata):
        data = self.load()
        if server_id not in data:
            data[server_id] = {}
        # Prevent duplicate registration: check if email already exists in this server.
        for existing_username, details in data[server_id].items():
            if details.get("email") == authdata.get("email"):
                return False
        if username not in data[server_id]:
            data[server_id][username] = authdata
            self.save(data)
            return True
        return False

    def login(self, server_id, username, authdata):
        data = self.load()
        if (server_id in data and username in data[server_id] and
            data[server_id][username].get("sub") == authdata.get("sub")):
            return True
        return False
