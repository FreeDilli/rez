# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from functools import wraps
from utils.logging_config import setup_logging
from models.database import get_db
from models.User import User
from utils.constants import VALID_ROLES, MIN_PASSWORD_LENGTH
import logging
from datetime import datetime
import sqlite3

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f"Checking role for route {f.__name__}, allowed roles: {allowed_roles}")
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            if current_user.role not in allowed_roles:
                logger.warning(f"Unauthorized role access attempt by {current_user.username} (role: {current_user.role}) to {request.path}")
                try:
                    with get_db() as db:
                        db.execute(
                            'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                            (current_user.username, 'unauthorized_access', request.path, f'Role {current_user.role} not in {allowed_roles}')
                        )
                        db.commit()
                except sqlite3.Error as e:
                    logger.error(f"Failed to log unauthorized access to audit_log: {str(e)}")
                flash("You do not have permission to access this page.", "danger")
                return render_template('403.html', message='Access Denied'), 403
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

        if not username or not password:
            flash("Username and password are required.", "danger")
            _log_audit(username, 'login_failed', 'Missing username or password')
            return render_template('login.html')

        if len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            _log_audit(username, 'login_failed', f'Password less than {MIN_PASSWORD_LENGTH} characters')
            return render_template('login.html')

        try:
            with get_db() as db:
                cursor = db.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
                user_data = cursor.fetchone()

                if user_data and check_password_hash(user_data['password'], password):
                    user_obj = User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
                    login_user(user_obj)

                    db.execute("UPDATE users SET last_login = ? WHERE username = ?", (datetime.utcnow(), username))
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username, 'login_success', 'login', f'Successful login, role: {user_data["role"]}')
                    )
                    db.commit()

                    flash("Login successful!", "success")
                    logger.info(f"Successful login for username: {username}, role: {user_data['role']}")
                    return redirect(url_for('dashboard.dashboard'))
                else:
                    flash("Invalid username or password", "danger")
                    _log_audit(username, 'login_failed', 'Invalid username or password')

        except sqlite3.Error as e:
            flash("Database error. Please try again later.", "danger")
            logger.error(f"Database error during login for username {username}: {str(e)}")
            _log_audit(username or 'Unknown', 'login_failed', f'Database error: {str(e)}')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logger.debug("Accessing /logout route")
    logger.info(f"User {current_user.username} logged out")
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('auth.login'))

def _log_audit(username, action, details):
    """Helper function to log audit events."""
    try:
        with get_db() as db:
            db.execute(
                'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                (username, action, 'login', details)
            )
            db.commit()
            logger.info(f"Audit log entry created: {username} {action} {details}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for {username}: {str(e)}")
