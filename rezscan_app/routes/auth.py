from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from rezscan_app.utils.constants import ROLE_REDIRECTS, MIN_PASSWORD_LENGTH
from rezscan_app.models.database import get_db
from rezscan_app.models.User import User
import logging
from datetime import datetime
import sqlite3
from rezscan_app.config import Config
import pytz

# Setup logging
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def log_audit_action(username, action, target, details=None):
    """Insert an audit log entry into the audit_log table."""
    try:
        with get_db() as conn:
            conn.execute(
                'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                (username, action, target, details)
            )
            conn.commit()
            logger.debug(f"Audit log created: {username} - {action} - {target}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for {username}: {str(e)}")

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = current_user.username if current_user.is_authenticated else 'anonymous'
            logger.debug(f"User {username} checking role for route {f.__name__}, allowed roles: {allowed_roles}")
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated access attempt to {request.path}")
                flash("Please log in to access this page.", "warning")
                log_audit_action(
                    username='anonymous',
                    action='unauthenticated_access',
                    target=request.path,
                    details=f'Attempted access to {request.path} without login'
                )
                return redirect(url_for('auth.login'))
            if current_user.role not in allowed_roles:
                logger.warning(f"User {username} (role: {current_user.role}) attempted unauthorized access to {request.path}")
                log_audit_action(
                    username=username,
                    action='unauthorized_access',
                    target=request.path,
                    details=f'Role {current_user.role} not in allowed roles {allowed_roles}'
                )
                flash("You do not have permission to access this page.", "danger")
                return render_template('403.html', message='Access Denied'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    username = 'anonymous'
    logger.debug(f"User {username} accessing /login route with method: {request.method}")
    
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        logger.debug(f"Login attempt for username: {username}")

        if not username or not password:
            logger.warning(f"Login failed for username {username}: Missing username or password")
            flash("Username and password are required.", "warning")
            log_audit_action(
                username=username,
                action='login_failed',
                target='login',
                details='Missing username or password'
            )
            return render_template('login.html')

        if len(password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"Login failed for username {username}: Password too short")
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "warning")
            log_audit_action(
                username=username,
                action='login_failed',
                target='login',
                details=f'Password less than {MIN_PASSWORD_LENGTH} characters'
            )
            return render_template('login.html')

        try:
            user = User.authenticate(username, password)
            if user:
                login_user(user)
                local_tz = pytz.timezone(Config.TIMEZONE)
                local_now = datetime.now(local_tz)
                last_login = local_now.strftime('%Y-%m-%d %H:%M:%S')
                with get_db() as conn:
                    conn.execute("UPDATE users SET last_login = ? WHERE username = ?", (last_login, username))
                    conn.commit()
                logger.info(f"User {username} logged in successfully, role: {user.role}, last_login: {last_login}")
                log_audit_action(
                    username=username,
                    action='login_success',
                    target='login',
                    details=f'Successful login, role: {user.role}, last_login: {last_login}'
                )
                flash("Login successful!", "success")
                redirect_endpoint = ROLE_REDIRECTS.get(user.role, 'dashboard.dashboard')
                return redirect(url_for(redirect_endpoint))
            else:
                logger.warning(f"Login failed for username {username}: Invalid username or password")
                flash("Invalid username or password", "warning")
                log_audit_action(
                    username=username,
                    action='login_failed',
                    target='login',
                    details='Invalid username or password'
                )
                return render_template('login.html')

        except sqlite3.Error as e:
            logger.error(f"Database error during login for username {username}: {str(e)}")
            log_audit_action(
                username=username,
                action='error',
                target='login',
                details=f"Database error during login: {str(e)}"
            )
            flash("Database error. Please try again later.", "danger")
            return render_template('login.html')

    log_audit_action(
        username=username,
        action='view',
        target='login',
        details='Accessed login page'
    )
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /logout route")
    logger.info(f"User {username} logged out")
    local_tz = pytz.timezone(Config.TIMEZONE)
    local_now = datetime.now(local_tz)
    log_audit_action(
        username=username,
        action='logout',
        target='logout',
        details=f'User logged out successfully at {local_now.strftime("%Y-%m-%d %H:%M:%S")}'
    )
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('auth.login'))