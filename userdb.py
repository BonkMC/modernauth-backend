import json

class UserDB:
    def __init__(self, filename="data/database.json"):
        self.filename = filename
        # Structure: { server_id: { username: authdata, ... }, ... }
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
            json.dump(self.data, f, indent=4)

    def signup(self, server_id, username, authdata):
        if server_id not in self.data:
            self.data[server_id] = {}
        if username not in self.data[server_id]:
            self.data[server_id][username] = authdata
            self.save()
            return True
        return False

    def login(self, server_id, username, authdata):
        if (server_id in self.data and username in self.data[server_id] and
            self.data[server_id][username].get("sub") == authdata.get("sub")):
            return True
        return False
