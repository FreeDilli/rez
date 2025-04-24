from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from functools import wraps
from config import Config
from utils.logging_config import setup_logging
from models.database import get_db
import logging
from datetime import datetime
import sqlite3  # Ensure sqlite3 is imported

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Checking login for route {f.__name__}")
        if 'user_id' not in session:
            logger.warning("Unauthorized access attempt; redirecting to login")
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f"Checking role for route {f.__name__}, allowed roles: {allowed_roles}")
            if 'user_id' not in session:
                logger.warning("Unauthorized access attempt; redirecting to login")
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            role = session.get('role')
            if role not in allowed_roles:
                logger.warning(f"Unauthorized role access attempt by {session.get('username', 'Unknown')} (role: {role}) to {request.path}")
                db = get_db()
                db.execute(
                    'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                    (session.get('username', 'Unknown'), 'unauthorized_access', request.path, f'Role {role} not in {allowed_roles}')
                )
                db.commit()
                flash("You do not have permission to access this page.", "danger")
                return render_template('error.html', message='Access Denied'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug(f"Accessing /login route with method: {request.method}")
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        logger.debug(f"Login attempt for username: {username}")
        try:
            db = get_db()
            cursor = db.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                db.execute("UPDATE users SET last_login = ? WHERE username = ?", (datetime.utcnow(), username))
                db.commit()
                logger.info(f"Successful login for username: {username}, role: {user['role']}, last_login updated")
                logger.debug(f"Session set: user_id={user['id']}, username={username}, role={user['role']}")
                flash("Login successful!", "success")
                return redirect(url_for('dashboard.dashboard'))
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                flash("Invalid username or password", "danger")
        except sqlite3.Error as e:
            logger.error(f"Database error during login for username {username}: {str(e)}")
            flash("Database error. Please try again later.", "danger")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logger.debug("Accessing /logout route")
    logger.info(f"User {session.get('username', 'Unknown')} logged out")
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('auth.login'))