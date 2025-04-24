import os, json, bcrypt
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class ServerConfig:
    def __init__(self, mysql_connection):
        # ensure we use PyMySQL driver
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()

        # new schema: server_id + secret_hash (bcrypt)
        self.config_table = Table(
            'server_config', self.metadata,
            Column('server_id', String(255), primary_key=True, nullable=False),
            Column('secret_hash', String(128), nullable=False)
        )
        self.metadata.create_all(self.engine)

    def load(self):
        """
        Returns dict { server_id: secret_hash }.
        """
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self.config_table.select()).mappings()
                return {r['server_id']: r['secret_hash'] for r in rows}
        except SQLAlchemyError:
            return {}

    def save(self, data):
        """
        data: { server_id: secret_hash }.
        Clears & repopulates table.
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(self.config_table.delete())
                for server_id, secret_hash in data.items():
                    conn.execute(
                        self.config_table.insert().values(
                            server_id=server_id,
                            secret_hash=secret_hash
                        )
                    )
            return True
        except SQLAlchemyError:
            return False

    def set_secret(self, server_id, raw_secret):
        """
        Hashes raw_secret (bcrypt) and stores it.
        """
        hashed = bcrypt.hashpw(raw_secret.encode(), bcrypt.gensalt()).decode()
        cfg = self.load()
        cfg[server_id] = hashed
        return self.save(cfg)

    def verify_secret(self, server_id, provided_secret):
        """
        Returns True if provided_secret matches the stored bcrypt hash.
        """
        cfg = self.load()
        secret_hash = cfg.get(server_id)
        if not secret_hash:
            return False
        return bcrypt.checkpw(provided_secret.encode(), secret_hash.encode())
