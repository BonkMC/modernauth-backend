import json
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class AdminDB:
    def __init__(self, mysql_connection, hash_function):
        # Ensure the connection string uses PyMySQL.
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        self.hash = hash_function

        # Store only hashed user_sub as the key
        self.admin_table = Table(
            'admindb', self.metadata,
            Column('user_sub', String(255), primary_key=True, nullable=False),  # hashed sub
            Column('data', String(4096))  # JSON record
        )
        self.metadata.create_all(self.engine)

    def _h(self, sub: str) -> str:
        return self.hash(sub)

    def load(self):
        """
        Returns { hashed_sub: record_dict }
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                for row in conn.execute(self.admin_table.select()).mappings():
                    try:
                        rec = json.loads(row['data'])
                    except Exception:
                        rec = {}
                    data[row['user_sub']] = rec
        except SQLAlchemyError:
            return {}
        return data

    def save(self, data):
        """
        Accepts { hashed_sub: record_dict } and writes it back.
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(self.admin_table.delete())
                for hsub, rec in data.items():
                    conn.execute(
                        self.admin_table.insert().values(
                            user_sub=hsub,
                            data=json.dumps(rec)
                        )
                    )
        except SQLAlchemyError:
            return False
        return True

    def is_admin(self, user_sub):
        data = self.load()
        rec = data.get(self._h(user_sub))
        return bool(rec and rec.get("is_admin", False))

    def is_manager(self, user_sub):
        data = self.load()
        rec = data.get(self._h(user_sub))
        return bool(rec and not rec.get("is_admin", False) and rec.get("servers"))

    def get_accessible_servers(self, user_sub):
        rec = self.load().get(self._h(user_sub), {})
        if rec.get("is_admin"):
            return "all"
        return rec.get("servers", [])

    def set_admin(self, user_sub, is_admin, servers=None, email=""):
        if servers is None:
            servers = []
        data = self.load()
        data[self._h(user_sub)] = {
            "is_admin": is_admin,
            "servers": servers,
            "email": email
        }
        return self.save(data)

    def add_access(self, user_sub, email, server_id, is_admin=False):
        data = self.load()
        # Prevent duplicate email on same server
        for rec in data.values():
            if server_id in rec.get("servers", []) and rec.get("email") == email:
                return False

        hsub = self._h(user_sub)
        rec = data.get(hsub, {"is_admin": False, "servers": [], "email": email})
        rec["email"] = email
        if server_id not in rec["servers"]:
            rec["servers"].append(server_id)
        if is_admin:
            rec["is_admin"] = True

        data[hsub] = rec
        return self.save(data)