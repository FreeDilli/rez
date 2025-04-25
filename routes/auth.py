from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from functools import wraps
from utils.logging_config import setup_logging
from models.database import get_db
import logging
from datetime import datetime
import sqlite3
from utils.constants import VALID_ROLES, MIN_PASSWORD_LENGTH

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
            if role not in allowed_roles or role not in VALID_ROLES:
                logger.warning(f"Unauthorized role access attempt by {session.get('username', 'Unknown')} (role: {role}) to {request.path}")
                try:
                    with get_db() as db:
                        db.execute(
                            'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                            (session.get('username', 'Unknown'), 'unauthorized_access', request.path, f'Role {role} not in {allowed_roles}')
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
            logger.warning(f"Login failed for username {username}: Missing username or password")
            try:
                with get_db() as db:
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username or 'Unknown', 'login_failed', 'login', 'Missing username or password')
                    )
                    db.commit()
            except sqlite3.Error as e:
                logger.error(f"Failed to log login attempt to audit_log: {str(e)}")
            flash("Username and password are required.", "danger")
            return render_template('login.html')
        if len(password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"Login failed for username {username}: Password too short")
            try:
                with get_db() as db:
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username, 'login_failed', 'login', f'Password less than {MIN_PASSWORD_LENGTH} characters')
                    )
                    db.commit()
            except sqlite3.Error as e:
                logger.error(f"Failed to log login attempt to audit_log: {str(e)}")
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return render_template('login.html')
        if not username.isalnum():
            logger.warning(f"Login failed for username {username}: Invalid username format")
            try:
                with get_db() as db:
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username, 'login_failed', 'login', 'Invalid username format')
                    )
                    db.commit()
            except sqlite3.Error as e:
                logger.error(f"Failed to log login attempt to audit_log: {str(e)}")
            flash("Username must be alphanumeric.", "danger")
            return render_template('login.html')

        try:
            with get_db() as db:
                cursor = db.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                if user and check_password_hash(user['password'], password):
                    session.permanent = True
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    db.execute("UPDATE users SET last_login = ? WHERE username = ?", (datetime.utcnow(), username))
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username, 'login_success', 'login', f'Successful login, role: {user["role"]}')
                    )
                    db.commit()
                    logger.info(f"Successful login for username: {username}, role: {user['role']}, last_login updated")
                    flash("Login successful!", "success")
                    return redirect(url_for('dashboard.dashboard'))
                else:
                    logger.warning(f"Failed login attempt for username: {username}")
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username, 'login_failed', 'login', 'Invalid username or password')
                    )
                    db.commit()
                    flash("Invalid username or password", "danger")
        except sqlite3.Error as e:
            logger.error(f"Database error during login for username {username}: {str(e)}")
            try:
                with get_db() as db:
                    db.execute(
                        'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                        (username or 'Unknown', 'login_failed', 'login', f'Database error: {str(e)}')
                    )
                    db.commit()
            except sqlite3.Error as e2:
                logger.error(f"Failed to log login attempt to audit_log: {str(e2)}")
            flash("Database error. Please try again later.", "danger")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logger.debug("Accessing /logout route")
    logger.info(f"User {session.get('username', 'Unknown')} logged out")
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('auth.login'))