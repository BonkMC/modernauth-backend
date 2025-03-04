import json

class AdminDB:
    def __init__(self, filename="data/admindb.json"):
        self.filename = filename
        # Data structure: { user_sub: { "is_admin": bool, "email": str, "servers": [server_id, ...] } }
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

    def is_admin(self, user_sub):
        admin = self.data.get(user_sub)
        if admin:
            return admin.get("is_admin", False)
        return False

    def is_manager(self, user_sub):
        admin = self.data.get(user_sub)
        if admin:
            # A manager is defined as not being a full admin but having an allowed server list.
            return not admin.get("is_admin", False) and bool(admin.get("servers"))
        return False

    def get_accessible_servers(self, user_sub):
        admin = self.data.get(user_sub)
        if admin:
            if admin.get("is_admin", False):
                return "all"  # signifies full access to all servers
            else:
                return admin.get("servers", [])
        return []

    def set_admin(self, user_sub, is_admin, servers=None, email=""):
        if servers is None:
            servers = []
        self.data[user_sub] = {"is_admin": is_admin, "servers": servers, "email": email}
        self.save()

    def add_access(self, user_sub, email, server_id, is_admin=False):
        # Prevent duplicate email for the same server.
        for uid, record in self.data.items():
            if server_id in record.get("servers", []):
                if record.get("email") == email:
                    return False
        if user_sub in self.data:
            record = self.data[user_sub]
            record["email"] = email
            if server_id not in record.get("servers", []):
                record["servers"].append(server_id)
            if is_admin:
                record["is_admin"] = True
        else:
            self.data[user_sub] = {"is_admin": is_admin, "servers": [server_id], "email": email}
        self.save()
        return True
