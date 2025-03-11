import time
import json
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class TokenSystemDB:
    def __init__(self, mysql_connection):
        # Ensure the connection string uses PyMySQL.
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        # Define the "tokensystem" table with token as primary key.
        self.tokens = Table(
            'tokensystem', self.metadata,
            Column('token', String(255), primary_key=True, nullable=False),
            Column('data', String(4096))  # Stores the token data as a JSON string.
        )
        self.metadata.create_all(self.engine)

    def load(self):
        """
        Reads all token data from the MySQL table and returns a dictionary in the format:
        { token: token_data_dict }
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.tokens.select()).mappings()
                for row in result:
                    try:
                        token_data = json.loads(row['data'])
                    except Exception:
                        token_data = {}
                    data[row['token']] = token_data
        except SQLAlchemyError:
            return {}
        return data

    def save(self, data):
        """
        Clears the current MySQL table and repopulates it using the given data dictionary.
        The data dictionary is expected to be in the format:
        { token: token_data_dict }
        """
        try:
            with self.engine.begin() as conn:
                # Clear existing data.
                conn.execute(self.tokens.delete())
                # Insert every token from the dictionary.
                for token, token_data in data.items():
                    token_json = json.dumps(token_data)
                    ins = self.tokens.insert().values(
                        token=token,
                        data=token_json
                    )
                    conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def _purge_expired_tokens(self, data):
        now = time.time()
        return {k: v for k, v in data.items() if v.get("expiration_time", 0) > now}

    def create_token(self, username, token, server_id, ttl=600, extra_data=None):
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
        data[token] = token_data
        self.save(data)
        return token

    def remove_token(self, token):
        data = self.load()
        if token in data:
            del data[token]
            self.save(data)

    def purge_expired_tokens(self):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)

    def check_token(self, token):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)
        return data[token]["username"] if token in data else None

    def get_token_data(self, token):
        data = self.load()
        data = self._purge_expired_tokens(data)
        self.save(data)
        return data.get(token, None)

    def authorize_token(self, token):
        data = self.load()
        data = self._purge_expired_tokens(data)
        if token in data:
            data[token]["authorized"] = True
            self.save(data)
