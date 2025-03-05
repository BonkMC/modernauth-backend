import json

class ServerConfig:
    def __init__(self, filename="data/server_config.json"):
        self.filename = filename
        self.config = self.load()

    def load(self):
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, server_id=None):
        # Always reload the config to capture any external changes.
        self.config = self.load()
        if server_id is None:
            return self.config
        return self.config.get(server_id, {})

    def add_server(self, server_id, secret_key):
        if server_id in self.config:
            return False
        self.config[server_id] = {"secret_key": secret_key}
        self.save()
        return True

    def update_secret(self, server_id, secret_key):
        if server_id not in self.config:
            return False
        self.config[server_id]["secret_key"] = secret_key
        self.save()
        return True

    def has_server(self, server_id):
        self.config = self.load()
        return server_id in self.config
