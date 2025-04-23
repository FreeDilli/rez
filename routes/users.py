from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import sqlite3
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from utils.logging_config import setup_logging
import logging
import os

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)
DB_PATH = Config.DB_PATH
VALID_ROLES = ['admin', 'viewer']  # Define valid roles
MIN_PASSWORD_LENGTH = 8  # Minimum password length

def log_audit_action(username, action, target, details=None):
    """Helper function to log actions to audit_log table and logger."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)",
                (username, action, target, details)
            )
            conn.commit()
            logger.info(f"Audit log: {username} performed '{action}' on '{target}'{f' - {details}' if details else ''}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for '{username}' on '{target}': {str(e)}")

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
            if len(password) < MIN_PASSWORD_LENGTH:
                logger.warning(f"Failed to add user '{username}': Password too short")
                flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
                return render_template('users.html', users=get_users())
            if role not in VALID_ROLES:
                logger.warning(f"Failed to add user '{username}': Invalid role '{role}'")
                flash(f"Invalid role selected.", "danger")
                return render_template('users.html', users=get_users())
            hashed_password = generate_password_hash(password)
            logger.debug(f"Adding user '{username}' with role '{role}'")
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
                    conn.commit()
                    logger.info(f"User '{username}' added successfully with role '{role}'")
                    flash(f"User '{username}' added successfully.", "success")
                    log_audit_action(session.get('username'), "Added user", username, f"Role: {role}")
            except sqlite3.IntegrityError:
                logger.warning(f"Failed to add user '{username}': Username already exists")
                flash(f"User '{username}' already exists.", "danger")
            except sqlite3.Error as e:
                logger.error(f"Database error adding user '{username}': {str(e)}")
                flash(f"Database error adding user.", "danger")

    return render_template('users.html', users=get_users())

def get_users():
    """Helper function to fetch users."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT username, role, last_login FROM users ORDER BY username")
            users = c.fetchall()
            logger.debug(f"Fetched {len(users)} users from database")
            return users
    except sqlite3.Error as e:
        logger.error(f"Database error fetching users: {str(e)}")
        flash("Database error fetching users.", "danger")
        return []

@users_bp.route('/admin/users/edit/<username>', methods=['GET', 'POST'])
def edit_user(username):
    logger.debug(f"Accessing /admin/users/edit/{username} route with method: {request.method}")
    if request.method == 'POST':
        new_role = request.form.get('role').strip()
        if new_role not in VALID_ROLES:
            logger.warning(f"Failed to update role for '{username}': Invalid role '{new_role}'")
            flash(f"Invalid role selected.", "danger")
            return redirect(url_for('users.manage_users'))
        logger.debug(f"Updating role for user '{username}' to '{new_role}'")
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
                if c.rowcount == 0:
                    logger.warning(f"Failed to update role for '{username}': User not found")
                    flash(f"User '{username}' not found.", "danger")
                else:
                    conn.commit()
                    logger.info(f"Role for user '{username}' updated to '{new_role}'")
                    flash(f"Role for '{username}' updated to '{new_role}'.", "success")
                    log_audit_action(session.get('username'), "Updated role", username, f"New role: {new_role}")
        except sqlite3.Error as e:
            logger.error(f"Database error updating role for '{username}': {str(e)}")
            flash("Database error updating user role.", "danger")
        return redirect(url_for('users.manage_users'))

    # Fetch user data for GET request
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT username, role FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user:
                logger.warning(f"User '{username}' not found for edit")
                flash(f"User '{username}' not found.", "danger")
                return redirect(url_for('users.manage_users'))
    except sqlite3.Error as e:
        logger.error(f"Database error fetching user '{username}': {str(e)}")
        flash("Database error fetching user.", "danger")
        return redirect(url_for('users.manage_users'))

    # Verify template existence
    template_path = os.path.join('templates', 'edit_user.html')
    if not os.path.exists(template_path):
        logger.error(f"Template 'edit_user.html' not found at {template_path}")
        flash("Template not found.", "danger")
        return redirect(url_for('users.manage_users'))

    return render_template('edit_user.html', user=user)

@users_bp.route('/profile/change_password', methods=['GET', 'POST'])
def change_password():
    logger.debug(f"Accessing /profile/change_password route with method: {request.method}")
    if 'username' not in session:
        logger.warning("Unauthorized attempt to access change_password")
        flash("Please log in to change your password.", "danger")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        current_password = request.form.get('current_password').strip()
        new_password = request.form.get('new_password').strip()
        confirm_password = request.form.get('confirm_password').strip()
        username = session['username']

        if new_password != confirm_password:
            logger.warning(f"Password change failed for '{username}': Passwords do not match")
            flash("New passwords do not match.", "danger")
            return render_template('change_password.html')
        if len(new_password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"Password change failed for '{username}': Password too short")
            flash(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return render_template('change_password.html')

        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ?", (username,))
                user = c.fetchone()
                if not user:
                    logger.warning(f"User '{username}' not found during password change")
                    flash("User not found.", "danger")
                    return redirect(url_for('users.change_password'))

                if not check_password_hash(user['password'], current_password):
                    logger.warning(f"Password change failed for '{username}': Incorrect current password")
                    flash("Current password is incorrect.", "danger")
                    return render_template('change_password.html')

                hashed_new_password = generate_password_hash(new_password)
                c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_password, username))
                conn.commit()
                logger.info(f"Password changed successfully for user '{username}'")
                flash("Password changed successfully.", "success")
                log_audit_action(username, "Changed password", username)
                return redirect(url_for('users.change_password'))
        except sqlite3.Error as e:
            logger.error(f"Database error changing password for '{username}': {str(e)}")
            flash("Database error changing password.", "danger")

    return render_template('change_password.html')

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
                log_audit_action(session.get('username'), "Reset password", username)
    except sqlite3.Error as e:
        logger.error(f"Database error resetting password for '{username}': {str(e)}")
        flash("Database error resetting password.", "danger")
    return redirect(url_for('users.manage_users'))

@users_bp.route('/admin/users/delete/<username>', methods=['POST'])
def delete_user(username):
    logger.debug(f"Accessing /admin/users/delete/{username} route")
    if username == session.get('username'):
        logger.warning(f"User '{username}' attempted to delete their own account")
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('users.manage_users'))
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
                log_audit_action(session.get('username'), "Deleted user", username)
    except sqlite3.Error as e:
        logger.error(f"Database error deleting user '{username}': {str(e)}")
        flash("Database error deleting user.", "danger")
    return redirect(url_for('users.manage_users'))