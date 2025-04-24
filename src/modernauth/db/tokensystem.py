import os, time, json, hashlib, hmac
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class TokenSystemDB:
    def __init__(self, mysql_connection):
        # HMAC key used to hash tokens at rest
        # Set TOKEN_HMAC_KEY in your env (e.g. 32-byte base64)
        self.hmac_key = os.getenv("TOKEN_HMAC_KEY").encode()

        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        # Rename column to token_hash
        self.tokens = Table(
            'tokensystem', self.metadata,
            Column('token_hash', String(64), primary_key=True, nullable=False),
            Column('data', String(4096))
        )
        self.metadata.create_all(self.engine)

    def _hash_token(self, token: str) -> str:
        """Compute HMAC-SHA256(token) → hex digest."""
        return hmac.new(self.hmac_key, token.encode(), hashlib.sha256).hexdigest()

    def load(self):
        """Returns dict { token_hash: token_data_dict }."""
        data = {}
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self.tokens.select()).mappings()
                for row in rows:
                    try:
                        token_data = json.loads(row['data'])
                    except Exception:
                        token_data = {}
                    data[row['token_hash']] = token_data
        except SQLAlchemyError:
            return {}
        return data

    def save(self, data):
        """Expects data keyed by token_hash."""
        try:
            with self.engine.begin() as conn:
                conn.execute(self.tokens.delete())
                for token_hash, token_data in data.items():
                    ins = self.tokens.insert().values(
                        token_hash=token_hash,
                        data=json.dumps(token_data)
                    )
                    conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def _purge_expired(self, data):
        now = time.time()
        return {h: v for h, v in data.items() if v.get("expiration_time", 0) > now}

    def create_token(self, username, token, server_id, ttl=600, extra_data=None):
        """
        Returns the raw token to hand back to the user, but only the HMACed value is ever stored.
        """
        data = self.load()
        data = self._purge_expired(data)

        token_hash = self._hash_token(token)
        token_record = {
            "username": username,
            "server_id": server_id,
            "expiration_time": time.time() + ttl,
            "authorized": False
        }
        if extra_data:
            token_record.update(extra_data)

        data[token_hash] = token_record
        self.save(data)
        return token  # still hand back the raw token

    def get_token_data(self, token):
        """
        Lookup by hashing the incoming token.
        Returns the record or None.
        """
        data = self.load()
        data = self._purge_expired(data)
        self.save(data)

        h = self._hash_token(token)
        return data.get(h)

    def remove_token(self, token):
        h = self._hash_token(token)
        data = self.load()
        if h in data:
            del data[h]
            self.save(data)

    def check_token(self, token):
        data = self.load()
        data = self._purge_expired(data)
        self.save(data)

        h = self._hash_token(token)
        return data[h]["username"] if h in data else None

    def authorize_token(self, token):
        """Mark an existing token (by raw value) as authorized."""
        h = self._hash_token(token)
        data = self.load()
        data = self._purge_expired(data)
        if h in data:
            data[h]["authorized"] = True
            self.save(data)
