from flask_login import UserMixin
from rezscan_app.models.database import get_db

class User(UserMixin):
    def __init__(self, id, username, password, role):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        db = get_db()
        c = db.cursor()
        c.execute('SELECT id, username, password, role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        if user:
            return User(user['id'], user['username'], user['password'], user['role'])
        return None

    @staticmethod
    def get_by_username(username):
        db = get_db()
        c = db.cursor()
        c.execute('SELECT id, username, password, role FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        if user:
            return User(user['id'], user['username'], user['password'], user['role'])
        return None

