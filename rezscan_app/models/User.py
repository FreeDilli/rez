from flask_login import UserMixin
from rezscan_app.models.database import get_db

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password  # ✅ ADD this line
        self.role = role

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, password, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            return User(id=user['id'], username=user['username'], password=user['password'], role=user['role'])
        return None

    @staticmethod
    def get_by_username(username):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            return User(id=user['id'], username=user['username'], password=user['password'], role=user['role'])
        return None
