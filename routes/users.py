from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
from config import Config
from werkzeug.security import generate_password_hash
from Utils.logging_config import setup_logging
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)
DB_PATH = Config.DB_PATH

@users_bp.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    logger.debug(f"Accessing /admin/users route with method: {request.method}")
    message = None

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').strip()
        role = request.form.get('role').strip()
        logger.debug(f"Processing action '{action}' for username: {username}, role: {role}")

        if action == 'add':
            password = request.form.get('password').strip()
            hashed_password = generate_password_hash(password)
            logger.debug(f"Adding user '{username}' with role '{role}'")
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
                    conn.commit()
                    logger.info(f"User '{username}' added successfully with role '{role}'")
                    flash(f"User '{username}' added successfully.", "success")
            except sqlite3.IntegrityError:
                logger.warning(f"Failed to add user '{username}': Username already exists")
                flash(f"User '{username}' already exists.", "danger")
            except sqlite3.Error as e:
                logger.error(f"Database error adding user '{username}': {str(e)}")
                flash(f"Database error adding user.", "danger")

    # Fetch current users
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # Enables dict-like access
            c = conn.cursor()
            c.execute("SELECT username, role FROM users ORDER BY username")
            users = c.fetchall()
            logger.debug(f"Fetched {len(users)} users from database")
    except sqlite3.Error as e:
        logger.error(f"Database error fetching users: {str(e)}")
        flash("Database error fetching users.", "danger")
        users = []

    return render_template('users.html', users=users)

@users_bp.route('/admin/users/reset/<username>', methods=['POST'])
def reset_password(username):
    logger.debug(f"Accessing /admin/users/reset/{username} route")
    new_password = generate_password_hash("temp1234")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
            if c.rowcount == 0:
                logger.warning(f"Failed to reset password for '{username}': User not found")
                flash(f"User '{username}' not found.", "danger")
            else:
                conn.commit()
                logger.info(f"Password reset for user '{username}' to 'temp1234'")
                flash(f"Password for '{username}' reset to 'temp1234'.", "info")
    except sqlite3.Error as e:
        logger.error(f"Database error resetting password for '{username}': {str(e)}")
        flash("Database error resetting password.", "danger")
    return redirect(url_for('users.manage_users'))

@users_bp.route('/admin/users/delete/<username>', methods=['POST'])
def delete_user(username):
    logger.debug(f"Accessing /admin/users/delete/{username} route")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            if c.rowcount == 0:
                logger.warning(f"Failed to delete user '{username}': User not found")
                flash(f"User '{username}' not found.", "danger")
            else:
                conn.commit()
                logger.info(f"User '{username}' deleted successfully")
                flash(f"User '{username}' deleted.", "warning")
    except sqlite3.Error as e:
        logger.error(f"Database error deleting user '{username}': {str(e)}")
        flash("Database error deleting user.", "danger")
    return redirect(url_for('users.manage_users'))