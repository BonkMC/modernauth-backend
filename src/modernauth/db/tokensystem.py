import time
import json
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class TokenSystemDB:
    def __init__(self, mysql_connection, hash_function):
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        self.hash = hash_function

        self.tokens = Table(
            'tokensystem', self.metadata,
            Column('token', String(255), primary_key=True, nullable=False),
            Column('data', String(4096))
        )
        self.metadata.create_all(self.engine)

    def _h(self, token: str) -> str:
        return self.hash(token)

    def load(self):
        data = {}
        try:
            with self.engine.connect() as conn:
                for row in conn.execute(self.tokens.select()).mappings():
                    try:
                        token_data = json.loads(row['data'])
                    except Exception:
                        token_data = {}
                    data[row['token']] = token_data
        except SQLAlchemyError:
            return {}
        return data

    def save(self, data):
        try:
            with self.engine.begin() as conn:
                conn.execute(self.tokens.delete())
                for htok, token_data in data.items():
                    ins = self.tokens.insert().values(
                        token=htok,
                        data=json.dumps(token_data)
                    )
                    conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def _purge_expired_tokens(self, data):
        now = time.time()
        return {k: v for k, v in data.items() if v.get("expiration_time", 0) > now}

    def create_token(self, username, token, server_id, ttl=600, extra_data=None):
        htok = self._h(token)
        data = self.load()
        data = self._purge_expired_tokens(data)
        token_data = {
            "username": username,
            "server_id": server_id,
            "expiration_time": time.time() + ttl,
            "authorized": False
        }
        if extra_data:
            token_data.update(extra_data)
        data[htok] = token_data
        self.save(data)
        return token

    def remove_token(self, token):
        htok = self._h(token)
        data = self.load()
        if htok in data:
            del data[htok]
            self.save(data)

    def purge_expired_tokens(self):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)

    def check_token(self, token):
        htok = self._h(token)
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)
        return data[htok]["username"] if htok in data else None

    def get_token_data(self, token):
        htok = self._h(token)
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)
        return data.get(htok)

    def authorize_token(self, token):
        htok = self._h(token)
        data = self.load()
        data = self._purge_expired_tokens(data)
        if htok in data:
            data[htok]["authorized"] = True
            self.save(data)