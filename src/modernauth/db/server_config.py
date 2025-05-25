import json
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

def make_engine_with_env_ssl(url):
    return create_engine(
        url=url.replace("mysql://", "mysql+pymysql://"),
        echo=False
    )


class ServerConfig:
    def __init__(self, mysql_connection, hash_function):
        self.engine = make_engine_with_env_ssl(mysql_connection)
        self.metadata = MetaData()
        self.create_hash = hash_function
        self.config_table = Table(
            'server_config', self.metadata,
            Column('server_id', String(255), primary_key=True, nullable=False),
            Column('config', String(4096))
        )
        self.metadata.create_all(self.engine)

    def load(self):
        try:
            data = {}
            with self.engine.connect() as conn:
                result = conn.execute(self.config_table.select()).mappings()
                for row in result:
                    try:
                        config_data = json.loads(row['config'])
                    except Exception:
                        config_data = {}
                    data[row['server_id']] = config_data
            return data
        except SQLAlchemyError:
            return {}

    def save(self, config):
        try:
            with self.engine.begin() as conn:
                conn.execute(self.config_table.delete())
                for server_id, conf in config.items():
                    conf_json = json.dumps(conf)
                    ins = self.config_table.insert().values(
                        server_id=server_id,
                        config=conf_json
                    )
                    conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def get_secret(self, server_id):
        config = self.load()
        return config.get(server_id, {}).get("secret_key")

    def update_secret(self, server_id, new_secret):
        config = self.load()
        if server_id in config:
            config[server_id]["secret_key"] = self.create_hash(new_secret)
            self.save(config)
            return True
        return False