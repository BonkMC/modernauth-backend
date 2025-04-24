import os, json, bcrypt
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class UserDB:
    def __init__(self, mysql_connection):
        # Ensure the connection string uses PyMySQL.
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        # Same schema: email & sub columns, plus authdata JSON.
        self.users = Table(
            'users', self.metadata,
            Column('server_id', String(255), primary_key=True, nullable=False),
            Column('username',  String(255), primary_key=True, nullable=False),
            Column('email',     String(128)),   # now holds bcrypt hash
            Column('sub',       String(128)),   # now holds bcrypt hash
            Column('authdata',  String(1024))   # still stores the full JSON
        )
        self.metadata.create_all(self.engine)

        # Optional: tune your bcrypt rounds via env
        self.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", 12))

    def _hash(self, val: str) -> str:
        """Return a bcrypt hash of val."""
        return bcrypt.hashpw(
            val.encode(),
            bcrypt.gensalt(rounds=self.bcrypt_rounds)
        ).decode()

    def _check(self, val: str, hashed: str) -> bool:
        """Verify bcrypt hash."""
        return bcrypt.checkpw(val.encode(), hashed.encode())

    def load(self):
        """
        Reads all user data from the authdata JSON column (plaintext!)
        and returns { server_id: { username: authdata_dict } }.
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(self.users.select()).mappings()
                for row in rows:
                    server_id = row['server_id']
                    username  = row['username']
                    try:
                        authdata = json.loads(row['authdata'])
                    except Exception:
                        authdata = {}
                    data.setdefault(server_id, {})[username] = authdata
        except SQLAlchemyError:
            return {}
        return data

    def save(self, data):
        """
        Clears & repopulates the table from a dict of authdata.
        Re–hashes email & sub on every save.
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(self.users.delete())
                for server_id, users in data.items():
                    for username, authdata in users.items():
                        email = authdata.get("email", "")
                        sub   = authdata.get("sub", "")
                        ins = self.users.insert().values(
                            server_id=server_id,
                            username=username,
                            email=self._hash(email) if email else None,
                            sub=self._hash(sub)     if sub   else None,
                            authdata=json.dumps(authdata)
                        )
                        conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def isuser(self, server_id, username):
        """
        True if (server_id, username) exists.
        """
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    (self.users.c.server_id == server_id) &
                    (self.users.c.username  == username)
                )
                return conn.execute(sel).mappings().fetchone() is not None
        except SQLAlchemyError:
            return False

    def signup(self, server_id, username, authdata):
        """
        - HMACs are *not* used here; we bcrypt-hash email & sub.
        - Duplicate-email check uses bcrypt.checkpw().
        """
        email_to_check = authdata.get("email", "")
        try:
            with self.engine.begin() as conn:
                # 1) Duplicate-email?
                sel = self.users.select().where(self.users.c.server_id == server_id)
                for row in conn.execute(sel).mappings():
                    if row['email'] and self._check(email_to_check, row['email']):
                        return False

                # 2) Username clash?
                sel2 = self.users.select().where(
                    (self.users.c.server_id == server_id) &
                    (self.users.c.username  == username)
                )
                if conn.execute(sel2).mappings().fetchone():
                    return False

                # 3) Insert new user with hashed email & sub
                ins = self.users.insert().values(
                    server_id=server_id,
                    username=username,
                    email=self._hash(email_to_check),
                    sub=self._hash(authdata.get("sub", "")),
                    authdata=json.dumps(authdata)
                )
                conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def login(self, server_id, username, authdata):
        """
        Verifies by bcrypt-checking the OIDC 'sub' value.
        """
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    (self.users.c.server_id == server_id) &
                    (self.users.c.username  == username)
                )
                row = conn.execute(sel).mappings().fetchone()
                if row and row['sub'] and self._check(authdata.get("sub", ""), row['sub']):
                    return True
        except SQLAlchemyError:
            return False
        return False
