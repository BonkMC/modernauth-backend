import sqlalchemy
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class UserDB:
    def __init__(self, mysql_connection, hash_function):
        # Ensure the connection string uses PyMySQL.
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        self.hash = hash_function

        # Table now stores only hashed username and hashed sub
        self.users = Table(
            'users', self.metadata,
            Column('server_id', String(255), primary_key=True, nullable=False),
            Column('username', String(255), primary_key=True, nullable=False),  # hash(username)
            Column('sub', String(255), nullable=False)                         # hash(sub)
        )
        self.metadata.create_all(self.engine)

    def _h(self, value: str) -> str:
        return self.hash(value)

    def signup(self, server_id: str, username: str, sub: str) -> bool:
        """
        Hashes username & sub, then inserts if username-hash not already taken.
        """
        h_user = self._h(username)
        h_sub = self._h(sub)
        try:
            with self.engine.begin() as conn:
                # Check for existing username-hash
                sel = self.users.select().where(
                    self.users.c.server_id == server_id,
                    self.users.c.username == h_user
                )
                if conn.execute(sel).first():
                    return False
                # Insert hashed values
                conn.execute(
                    self.users.insert().values(
                        server_id=server_id,
                        username=h_user,
                        sub=h_sub
                    )
                )
            return True
        except SQLAlchemyError:
            return False

    def isuser(self, server_id: str, username: str) -> bool:
        """
        Returns True if hash(username) exists for that server.
        """
        h_user = self._h(username)
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id,
                    self.users.c.username == h_user
                )
                return conn.execute(sel).first() is not None
        except SQLAlchemyError:
            return False

    def login(self, server_id: str, username: str, sub: str) -> bool:
        """
        Returns True if stored hash(sub) matches hash(sub) for that username.
        """
        h_user = self._h(username)
        h_sub = self._h(sub)
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id,
                    self.users.c.username == h_user,
                    self.users.c.sub      == h_sub
                )
                return conn.execute(sel).first() is not None
        except SQLAlchemyError:
            return False

    def delete(self, server_id: str, username: str) -> bool:
        """
        Deletes the row for hash(username).
        """
        h_user = self._h(username)
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.users.delete().where(
                        self.users.c.server_id == server_id,
                        self.users.c.username == h_user
                    )
                )
            return True
        except SQLAlchemyError:
            return False

    def load(self):
        """
        Returns the raw mapping of hashed_username→hashed_sub,
        for internal/admin use only.
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                for row in conn.execute(self.users.select()).mappings():
                    srv = row['server_id']
                    usr = row['username']
                    sb  = row['sub']
                    data.setdefault(srv, {})[usr] = sb
        except SQLAlchemyError:
            return {}
        return data