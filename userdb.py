import json
from sqlalchemy import create_engine, Table, Column, String, MetaData
from sqlalchemy.exc import SQLAlchemyError

class UserDB:
    def __init__(self, mysql_connection):
        # Create engine using the given MySQL connection string.
        self.engine = create_engine(mysql_connection, echo=False)
        self.metadata = MetaData()
        # Define a table with server_id and username as composite primary keys.
        # Also storing email and sub separately (extracted from authdata) for easier queries.
        # The full authdata is stored as a JSON string.
        self.users = Table(
            'users', self.metadata,
            Column('server_id', String(255), primary_key=True, nullable=False),
            Column('username', String(255), primary_key=True, nullable=False),
            Column('email', String(255)),
            Column('sub', String(255)),
            Column('authdata', String(1024))  # store authdata as a JSON string
        )
        # Create the table if it doesn't exist.
        self.metadata.create_all(self.engine)

    def load(self):
        """
        Reads all user data from the MySQL table and returns a dictionary in the format:
        { server_id: { username: authdata_dict } }
        """
        data = {}
        try:
            with self.engine.connect() as conn:
                result = conn.execute(self.users.select())
                for row in result:
                    server_id = row['server_id']
                    username = row['username']
                    try:
                        authdata = json.loads(row['authdata'])
                    except Exception:
                        authdata = {}
                    if server_id not in data:
                        data[server_id] = {}
                    data[server_id][username] = authdata
        except SQLAlchemyError:
            # In case of error, return empty dictionary
            return {}
        return data

    def save(self, data):
        """
        Clears the current MySQL table and repopulates it using the given data dictionary.
        The data dictionary is expected to be in the format:
        { server_id: { username: authdata_dict } }
        """
        try:
            with self.engine.begin() as conn:
                # Clear existing data.
                conn.execute(self.users.delete())
                # Insert every user from the dictionary.
                for server_id, users in data.items():
                    for username, authdata in users.items():
                        email = authdata.get("email")
                        sub = authdata.get("sub")
                        authdata_str = json.dumps(authdata)
                        ins = self.users.insert().values(
                            server_id=server_id,
                            username=username,
                            email=email,
                            sub=sub,
                            authdata=authdata_str
                        )
                        conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def isuser(self, server_id, username):
        """
        Checks if a user exists in the database.
        Returns True if found, False otherwise.
        """
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id
                ).where(
                    self.users.c.username == username
                )
                result = conn.execute(sel).fetchone()
                return result is not None
        except SQLAlchemyError:
            return False

    def signup(self, server_id, username, authdata):
        """
        Registers a new user if:
          - No user with the same email exists for the given server_id.
          - The username is not already taken for that server_id.
        Returns True on successful signup, False if registration fails.
        """
        email_to_check = authdata.get("email")
        try:
            with self.engine.begin() as conn:
                # Check for duplicate email in the same server.
                sel = self.users.select().where(
                    self.users.c.server_id == server_id
                )
                result = conn.execute(sel).fetchall()
                for row in result:
                    if row['email'] == email_to_check:
                        return False

                # Check if the username is already registered.
                sel = self.users.select().where(
                    self.users.c.server_id == server_id
                ).where(
                    self.users.c.username == username
                )
                if conn.execute(sel).fetchone():
                    return False

                # Insert new user.
                ins = self.users.insert().values(
                    server_id=server_id,
                    username=username,
                    email=email_to_check,
                    sub=authdata.get("sub"),
                    authdata=json.dumps(authdata)
                )
                conn.execute(ins)
            return True
        except SQLAlchemyError:
            return False

    def login(self, server_id, username, authdata):
        """
        Verifies the user login by checking if the 'sub' field matches for the given user.
        Returns True if the credentials match, False otherwise.
        """
        try:
            with self.engine.connect() as conn:
                sel = self.users.select().where(
                    self.users.c.server_id == server_id
                ).where(
                    self.users.c.username == username
                )
                row = conn.execute(sel).fetchone()
                if row and row['sub'] == authdata.get("sub"):
                    return True
        except SQLAlchemyError:
            return False
        return False
