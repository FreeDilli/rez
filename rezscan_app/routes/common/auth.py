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
from urllib.parse import urlparse, urljoin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re

# Setup logging
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# Initialize Limiter (configured in app.py)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def user_key_func():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            username = current_user.username if current_user.is_authenticated else 'anonymous'
            logger.debug(f"User {username} checking role for route {f.__name__}, allowed roles: {allowed_roles}")
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated access attempt to {request.path}")
                flash("Please log in to access this page.", "warning")
                from rezscan_app.utils.audit_logging import log_audit_action
                log_audit_action(
                    username='anonymous',
                    action='unauthenticated_access',
                    target=request.path,
                    details=f'Attempted access to {request.path} without login'
                )
                return redirect(url_for('auth.login'))
            if current_user.role not in allowed_roles:
                logger.warning(f"User {username} (role: {current_user.role}) attempted unauthorized access to {request.path}")
                from rezscan_app.utils.audit_logging import log_audit_action
                log_audit_action(
                    username=username,
                    action='unauthorized_access',
                    target=request.path,
                    details=f'Role {current_user.role} not in allowed roles {allowed_roles}'
                )
                flash("You do not have permission to access this page.", "danger")
                return render_template('common/403.html', message='Access Denied'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_safe_url(target):
    """Check if the target URL is safe to redirect to."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    ref_netloc = ref_url.netloc.split(':')[0]
    test_netloc = test_url.netloc.split(':')[0]
    is_safe = test_url.scheme in ('http', 'https') and ref_netloc == test_netloc
    logger.debug(f"is_safe_url: target={target}, is_safe={is_safe}")
    return is_safe

def get_role_redirect(user):
    """Get the redirect URL based on user's role."""
    return url_for(ROLE_REDIRECTS.get(user.role, 'dashboard.dashboard'))

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(get_role_redirect(current_user))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("50/hour", key_func=user_key_func)
def login():
    username = request.form.get('username', '').strip() if request.method == 'POST' else 'anonymous'
    logger.debug(f"User {username} accessing /login route with method: {request.method}")
    
    if request.method == 'POST':
        if not re.match(r'^[a-zA-Z0-9_]{1,50}$', username):
            logger.warning(f"Login failed for username {username}: Invalid username format")
            from rezscan_app.utils.audit_logging import log_audit_action
            log_audit_action(
                username=username,
                action='login_failed',
                target='login',
                details='Invalid username format'
            )
            flash("Invalid username format. Use alphanumeric characters and underscores, max 50 characters.", "warning")
            return render_template('common/login.html', next=request.form.get('next', request.args.get('next', '')))

        password = request.form.get('password', '').strip()
        logger.debug(f"Login attempt for username: {username}")

        if not username or not password:
            logger.warning(f"Login failed for username {username}: Missing username or password")
            from rezscan_app.utils.audit_logging import log_audit_action
            log_audit_action(
                username=username,
                action='login_failed',
                target='login',
                details='Missing username or password'
            )
            flash("Username and password are required.", "warning")
            return render_template('common/login.html', next=request.form.get('next', request.args.get('next', '')))

        if len(password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"Login failed for username {username}: Password too short")
            from rezscan_app.utils.audit_logging import log_audit_action
            log_audit_action(
                username=username,
                action='login_failed',
                target='login',
                details=f'Password less than {MIN_PASSWORD_LENGTH} characters'
            )
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "warning")
            return render_template('common/login.html', next=request.form.get('next', request.args.get('next', '')))

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
                from rezscan_app.utils.audit_logging import log_audit_action
                log_audit_action(
                    username=username,
                    action='login_success',
                    target='login',
                    details=f'Successful login, role: {user.role}, last_login: {last_login}'
                )
                flash("Login successful!", "success")
                next_page = request.form.get('next', request.args.get('next'))
                if next_page and is_safe_url(next_page):
                    logger.debug(f"Redirecting to: {next_page}")
                    return redirect(next_page)
                logger.debug(f"Using role-based redirect for role: {user.role}")
                return redirect(get_role_redirect(user))
            else:
                logger.warning(f"Login failed for username {username}: Invalid username or password")
                from rezscan_app.utils.audit_logging import log_audit_action
                log_audit_action(
                    username=username,
                    action='login_failed',
                    target='login',
                    details='Invalid username or password'
                )
                flash("Invalid username or password", "warning")
                return render_template('common/login.html', next=request.form.get('next', request.args.get('next', '')))

        except sqlite3.Error as e:
            logger.error(f"Database error during login for username {username}: {str(e)}")
            from rezscan_app.utils.audit_logging import log_audit_action
            log_audit_action(
                username=username,
                action='error',
                target='login',
                details=f"Database error during login: {str(e)}"
            )
            flash("Database error. Please try again later.", "danger")
            return render_template('common/login.html', next=request.form.get('next', request.args.get('next', '')))

    next_page = request.args.get('next', '')
    return render_template('common/login.html', next=next_page)

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /logout route")
    logger.info(f"User {username} logged out")
    local_tz = pytz.timezone(Config.TIMEZONE)
    local_now = datetime.now(local_tz)
    logout_user()
    from rezscan_app.utils.audit_logging import log_audit_action
    log_audit_action(
        username=username,
        action='logout',
        target='logout',
        details=f'User logged out successfully at {local_now.strftime("%Y-%m-%d %H:%M:%S")}'
    )
    flash("Logged out successfully.", "info")
    return redirect(url_for('auth.login'))