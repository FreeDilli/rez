from flask_login import UserMixin
from rezscan_app.models.database import get_db
from werkzeug.security import check_password_hash

class User(UserMixin):
    def __init__(self, id, username, role, theme=None):
        self.id = id
        self.username = username
        self.role = role
        self.theme = theme or 'dark'

    def get_id(self):
        return str(self.id)

    @staticmethod
    def get(user_id):
        if not user_id:
            return None
        try:
            user_id = int(user_id)
        except ValueError:
            return None
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, role, theme FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            return User(id=user['id'], username=user['username'], role=user['role'], theme=user['theme'])
        return None

    @staticmethod
    def authenticate(username, password):
        if not username or not isinstance(username, str) or not password:
            return None
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, password, role, theme FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user['password'], password):
            return User(id=user['id'], username=user['username'], role=user['role'], theme=user['theme'])
        return None