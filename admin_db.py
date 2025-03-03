import json

class AdminDB:
    def __init__(self, filename="data/admindb.json"):
        self.filename = filename
        # Data structure: { user_sub: { "is_admin": bool, "servers": [server_id, ...] } }
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

    def set_admin(self, user_sub, is_admin, servers=None):
        if servers is None:
            servers = []
        self.data[user_sub] = {"is_admin": is_admin, "servers": servers}
        self.save()

    def import_user(self, user_sub, server_id):
        """Import a user (by their Auth0 sub) as a manager for the given server."""
        if user_sub in self.data:
            if self.data[user_sub].get("is_admin"):
                # Already a full admin; no need to import.
                return
            if server_id not in self.data[user_sub].get("servers", []):
                self.data[user_sub]["servers"].append(server_id)
        else:
            # Create a new manager entry with the given server.
            self.data[user_sub] = {"is_admin": False, "servers": [server_id]}
        self.save()
