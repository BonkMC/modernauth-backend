import json
import os

class AdminDB:
    def __init__(self, filename="data/admindb.json"):
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

    def is_admin(self, user_sub):
        data = self.load()
        admin = data.get(user_sub)
        if admin:
            return admin.get("is_admin", False)
        return False

    def is_manager(self, user_sub):
        data = self.load()
        admin = data.get(user_sub)
        if admin:
            # A manager is defined as not being a full admin but having an allowed server list.
            return not admin.get("is_admin", False) and bool(admin.get("servers"))
        return False

    def get_accessible_servers(self, user_sub):
        data = self.load()
        admin = data.get(user_sub)
        if admin:
            if admin.get("is_admin", False):
                return "all"  # signifies full access to all servers
            else:
                return admin.get("servers", [])
        return []

    def set_admin(self, user_sub, is_admin, servers=None, email=""):
        if servers is None:
            servers = []
        data = self.load()
        data[user_sub] = {"is_admin": is_admin, "servers": servers, "email": email}
        self.save(data)

    def add_access(self, user_sub, email, server_id, is_admin=False):
        data = self.load()
        # Prevent duplicate email for the same server.
        for uid, record in data.items():
            if server_id in record.get("servers", []):
                if record.get("email") == email:
                    return False
        if user_sub in data:
            record = data[user_sub]
            record["email"] = email
            if server_id not in record.get("servers", []):
                record["servers"].append(server_id)
            if is_admin:
                record["is_admin"] = True
        else:
            data[user_sub] = {"is_admin": is_admin, "servers": [server_id], "email": email}
        self.save(data)
        return True
