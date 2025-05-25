from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

def make_engine_with_env_ssl(url):
    return create_engine(
        url=url.replace("mysql://", "mysql+pymysql://"),
        echo=False
    )

class UserDB:
    def __init__(self, mysql_connection, hash_function):
        self.engine = make_engine_with_env_ssl(mysql_connection)
        self.metadata = MetaData()
        self.hash = hash_function
        self.users = Table(
            'users', self.metadata,
            Column('server_id', String(255), primary_key=True, nullable=False),
            Column('username', String(255), primary_key=True, nullable=False),
            Column('sub', String(255), nullable=False)
        )
        self.metadata.create_all(self.engine)

    def _h(self, value: str) -> str:
        return self.hash(value)

    def signup(self, server_id: str, username: str, sub: str) -> bool:
        h_sub = self._h(sub)
        try:
            with self.engine.begin() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id,
                    self.users.c.username == username
                )
                if conn.execute(sel).first():
                    return False
                conn.execute(
                    self.users.insert().values(
                        server_id=server_id,
                        username=username,
                        sub=h_sub
                    )
                )
            return True
        except SQLAlchemyError:
            return False

    def isuser(self, server_id: str, username: str) -> bool:
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id,
                    self.users.c.username == username
                )
                return conn.execute(sel).first() is not None
        except SQLAlchemyError:
            return False

    def login(self, server_id: str, username: str, sub: str) -> bool:
        h_sub = self._h(sub)
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id,
                    self.users.c.username == username,
                    self.users.c.sub      == h_sub
                )
                return conn.execute(sel).first() is not None
        except SQLAlchemyError:
            return False

    def delete(self, server_id: str, username: str) -> bool:
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.users.delete().where(
                        self.users.c.server_id == server_id,
                        self.users.c.username == username
                    )
                )
            return True
        except SQLAlchemyError:
            return False

    def load(self):
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