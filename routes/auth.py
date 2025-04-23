from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import check_password_hash
from functools import wraps
from config import Config
from utils.logging_config import setup_logging
import logging
from datetime import datetime

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
DB_PATH = Config.DB_PATH

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

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug(f"Accessing /login route with method: {request.method}")
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        logger.debug(f"Login attempt for username: {username}")
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("SELECT id, password, role FROM users WHERE username = ?", (username,))
                user = c.fetchone()
                if user and check_password_hash(user[1], password):
                    session['user_id'] = user[0]
                    session['username'] = username
                    session['role'] = user[2]
                    c.execute("UPDATE users SET last_login = ? WHERE username = ?", (datetime.now(), username))
                    conn.commit()
                    logger.info(f"Successful login for username: {username}, role: {user[2]}, last_login updated")
                    logger.debug(f"Session set: user_id={user[0]}, username={username}, role={user[2]}")
                    flash("Login successful!", "success")
                    return redirect(url_for('dashboard.dashboard'))
                else:
                    logger.warning(f"Failed login attempt for username: {username}")
                    flash("Invalid username or password", "danger")
        except sqlite3.Error as e:
            logger.error(f"Database error during login for username {username}: {str(e)}")
            flash("Database error. Please try again later.", "danger")
            return render_template('login.html')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logger.debug("Accessing /logout route")
    logger.info(f"User {session.get('username', 'Unknown')} logged out")
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('auth.login'))