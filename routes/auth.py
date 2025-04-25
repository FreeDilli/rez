from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from models.database import get_db
from functools import wraps
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# 🛡️ Decorator: Requires login
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            session['next'] = request.url  # 🧭 Save where user tried to go
            return redirect(url_for('auth.login'))
        return view_func(*args, **kwargs)
    return wrapper

# 🧑‍⚖️ Decorator: Requires specific roles
def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash("Access denied: insufficient permissions", "danger")
                return redirect(url_for('auth.login'))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator

# 🔐 Login Route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session.pop('failed_attempts', None)  # ✅ Reset failed attempts

            # 🎯 Redirect to saved destination or by role
            redirect_to = session.pop('next', None)
            if redirect_to:
                return redirect(redirect_to)
            elif user['role'] == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            else:
                return redirect(url_for('dashboard.dashboard'))  # or scan.scan

        # 🚨 Track failed login attempts
        attempts = session.get('failed_attempts', {})
        attempts[username] = attempts.get(username, 0) + 1
        session['failed_attempts'] = attempts
        logger.warning(f"Failed login attempt for {username} (#{attempts[username]})")
        flash(f"Invalid credentials. Attempt #{attempts[username]}", "danger")

        return redirect(url_for('auth.login'))

    return render_template('login.html')

# 🚪 Logout Route
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))


