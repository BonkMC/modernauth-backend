import json

class UserDB:
    def __init__(self, filename="database.json"):
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
            json.dump(self.data, f, indent=4)

    def signup(self, username, authdata):
        if username not in self.data:
            self.data[username] = authdata
            self.save()
            return True
        return False

    def login(self, username, authdata):
        if username in self.data and self.data[username].get("sub") == authdata.get("sub"):
            return True
        return False
