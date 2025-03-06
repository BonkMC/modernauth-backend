import json
import os

class ServerConfig:
    def __init__(self, filename="data/server_config.json"):
        self.filename = filename
        # Ensure the file exists.
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump({}, f)

    def load(self):
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, config):
        with open(self.filename, "w") as f:
            json.dump(config, f, indent=4)

    def get_secret(self, server_id):
        config = self.load()
        return config.get(server_id, {}).get("secret_key")

    def update_secret(self, server_id, new_secret):
        config = self.load()
        if server_id in config:
            config[server_id]["secret_key"] = new_secret
            self.save(config)
            return True
        return False
