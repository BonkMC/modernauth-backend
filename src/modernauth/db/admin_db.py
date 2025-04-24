import os, json, bcrypt
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class AdminDB:
    def __init__(self, mysql_connection):
        # Bcrypt work factor (rounds); tune via env BCRYPT_ROUNDS
        self.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", 12))

        # Ensure the connection string uses PyMySQL.
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine   = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()

        # Same schema: user_sub PK + data JSON
        self.admin_table = Table(
            'admindb', self.metadata,
            Column('user_sub', String(255), primary_key=True, nullable=False),
            Column('data',     String(4096))  # JSON blob with is_admin, servers, email (now hashed)
        )
        self.metadata.create_all(self.engine)

    def _hash(self, val: str) -> str:
        """Bcrypt-hash the given value."""
        return bcrypt.hashpw(
            val.encode(),
            bcrypt.gensalt(rounds=self.bcrypt_rounds)
        ).decode()

    def _check(self, val: str, hashed: str) -> bool:
        """Verify a bcrypt hash."""
        return bcrypt.checkpw(val.encode(), hashed.encode())

    def load(self):
        """
        Reads all admin data from MySQL and returns { user_sub: record_dict }.
        Each record_dict has keys "is_admin", "servers", and a hashed "email".
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                for row in conn.execute(self.admin_table.select()).mappings():
                    try:
                        record = json.loads(row['data'])
                    except Exception:
                        record = {}
                    data[row['user_sub']] = record
        except SQLAlchemyError:
            return {}
        return data

    def save(self, data):
        """
        Clears the table and writes back the given dict.
        `data` should be { user_sub: {is_admin, servers, email_hash} }.
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(self.admin_table.delete())
                for user_sub, record in data.items():
                    rec_json = json.dumps(record)
                    conn.execute(
                        self.admin_table.insert().values(
                            user_sub=user_sub,
                            data=rec_json
                        )
                    )
            return True
        except SQLAlchemyError:
            return False

    def is_admin(self, user_sub):
        rec = self.load().get(user_sub, {})
        return rec.get("is_admin", False)

    def is_manager(self, user_sub):
        rec = self.load().get(user_sub, {})
        return not rec.get("is_admin", False) and bool(rec.get("servers"))

    def get_accessible_servers(self, user_sub):
        rec = self.load().get(user_sub, {})
        if rec.get("is_admin", False):
            return "all"
        return rec.get("servers", [])

    def set_admin(self, user_sub, is_admin, servers=None, email=""):
        """
        Create or overwrite an admin record.
        Hashes `email` before storing.
        """
        if servers is None:
            servers = []
        data = self.load()

        email_hash = self._hash(email) if email else ""
        data[user_sub] = {
            "is_admin": is_admin,
            "servers":  servers,
            "email":    email_hash
        }
        self.save(data)

    def add_access(self, user_sub, email, server_id, is_admin=False):
        """
        Grant manager/admin access.
        - Prevents duplicate email on the same server by bcrypt-checking each stored hash.
        - Stores only a bcrypt hash of the new email.
        """
        data = self.load()

        # Reject if any existing record for this server already has that email
        for uid, record in data.items():
            if server_id in record.get("servers", []):
                stored = record.get("email", "")
                if stored and self._check(email, stored):
                    return False

        # Add or update this user's record
        if user_sub in data:
            rec = data[user_sub]
            rec["email"] = self._hash(email)
            if server_id not in rec["servers"]:
                rec["servers"].append(server_id)
            if is_admin:
                rec["is_admin"] = True
        else:
            data[user_sub] = {
                "is_admin": is_admin,
                "servers":  [server_id],
                "email":    self._hash(email)
            }

        self.save(data)
        return True