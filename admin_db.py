import json
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class AdminDB:
    def __init__(self, mysql_connection):
        # Ensure the connection string uses PyMySQL.
        mysql_connection = mysql_connection.replace("mysql://", "mysql+pymysql://")
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        # Define the "admindb" table with user_sub as primary key.
        self.admin_table = Table(
            'admindb', self.metadata,
            Column('user_sub', String(255), primary_key=True, nullable=False),
            Column('data', String(4096))  # Stores the admin record as a JSON string.
        )
        self.metadata.create_all(self.engine)

    def load(self):
        """
        Reads all admin data from the MySQL table and returns a dictionary.
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.admin_table.select()).mappings()
                for row in result:
                    try:
                        record = json.loads(row['data'])
                    except Exception:
                        record = {}
                    data[row['user_sub']] = record
            return data
        except SQLAlchemyError:
            return {}

    def save(self, data):
        """
        Clears the current MySQL table and repopulates it using the given data dictionary.
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(self.admin_table.delete())
                for user_sub, record in data.items():
                    rec_json = json.dumps(record)
                    ins = self.admin_table.insert().values(
                        user_sub=user_sub,
                        data=rec_json
                    )
                    conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def is_admin(self, user_sub):
        data = self.load()
        admin = data.get(user_sub)
        if admin:
            return admin.get("is_admin", False)
        return False

    def is_manager(self, user_sub):
        data = self.load()
        admin = data.get(user_sub)
        if admin:
            # A manager is defined as not being a full admin but having an allowed server list.
            return not admin.get("is_admin", False) and bool(admin.get("servers"))
        return False

    def get_accessible_servers(self, user_sub):
        data = self.load()
        admin = data.get(user_sub)
        if admin:
            if admin.get("is_admin", False):
                return "all"  # signifies full access to all servers
            else:
                return admin.get("servers", [])
        return []

    def set_admin(self, user_sub, is_admin, servers=None, email=""):
        if servers is None:
            servers = []
        data = self.load()
        data[user_sub] = {"is_admin": is_admin, "servers": servers, "email": email}
        self.save(data)

    def add_access(self, user_sub, email, server_id, is_admin=False):
        data = self.load()
        # Prevent duplicate email for the same server.
        for uid, record in data.items():
            if server_id in record.get("servers", []):
                if record.get("email") == email:
                    return False
        if user_sub in data:
            record = data[user_sub]
            record["email"] = email
            if server_id not in record.get("servers", []):
                record["servers"].append(server_id)
            if is_admin:
                record["is_admin"] = True
        else:
            data[user_sub] = {"is_admin": is_admin, "servers": [server_id], "email": email}
        self.save(data)
        return True
