from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
from rezscan_app.utils.logging_config import setup_logging
from rezscan_app.utils.constants import (
    VALID_ROLES, MIN_PASSWORD_LENGTH
)
from rezscan_app.routes.auth import role_required
import logging
import sqlite3

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)

def log_audit_action(username, action, target, details=None):
    """Helper function to log actions to audit_log table and logger."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)",
                (username, action, target, details)
            )
            conn.commit()
            logger.debug(f"Audit log created: {username} - {action} - {target}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for {username}: {str(e)}")

@users_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_users():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/users route with method: {request.method}")
    
    if request.method == 'POST':
        action = request.form.get('action')
        target_username = request.form.get('username').strip()
        role = request.form.get('role').strip()
        logger.debug(f"User {username} processing action '{action}' for username: {target_username}, role: {role}")

        if action == 'add':
            password = request.form.get('password').strip()
            if len(password) < MIN_PASSWORD_LENGTH:
                logger.warning(f"User {username} failed to add user '{target_username}': Password too short")
                log_audit_action(
                    username=username,
                    action='add_user_failed',
                    target='users',
                    details=f"Failed to add user {target_username}: Password too short"
                )
                flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
                return render_template('users.html', users=get_users(), valid_roles=VALID_ROLES)
            if role not in VALID_ROLES:
                logger.warning(f"User {username} failed to add user '{target_username}': Invalid role '{role}'")
                log_audit_action(
                    username=username,
                    action='add_user_failed',
                    target='users',
                    details=f"Failed to add user {target_username}: Invalid role {role}"
                )
                flash(f"Invalid role selected.", "danger")
                return render_template('users.html', users=get_users(), valid_roles=VALID_ROLES)
            hashed_password = generate_password_hash(password)
            logger.debug(f"User {username} adding user '{target_username}' with role '{role}'")
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (target_username, hashed_password, role))
                    conn.commit()
                    logger.info(f"User {username} added user '{target_username}' with role '{role}'")
                    log_audit_action(
                        username=username,
                        action='add_user',
                        target='users',
                        details=f"Added user {target_username} with role {role}"
                    )
                    flash(f"User '{target_username}' added successfully.", "success")
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: users.username" in str(e):
                    logger.warning(f"User {username} failed to add user '{target_username}': Username already exists")
                    log_audit_action(
                        username=username,
                        action='add_user_failed',
                        target='users',
                        details=f"Failed to add user {target_username}: Username already exists"
                    )
                    flash(f"User '{target_username}' already exists.", "danger")
                else:
                    logger.error(f"User {username} failed to add user '{target_username}': Database integrity error - {str(e)}")
                    log_audit_action(
                        username=username,
                        action='error',
                        target='users',
                        details=f"Database integrity error adding user {target_username}: {str(e)}"
                    )
                    flash(f"Failed to add user due to database constraint violation.", "danger")
            except sqlite3.Error as e:
                logger.error(f"Database error for user {username} adding user '{target_username}': {str(e)}")
                log_audit_action(
                    username=username,
                    action='error',
                    target='users',
                    details=f"Database error adding user {target_username}: {str(e)}"
                )
                flash(f"Database error adding user.", "danger")
    else:
        log_audit_action(
            username=username,
            action='view',
            target='users',
            details='Viewed users management page'
        )

    users = get_users()
    logger.debug(f"User {username} fetched {len(users)} users")
    return render_template('users.html', users=users, valid_roles=VALID_ROLES)

def get_users():
    """Helper function to fetch users."""
    username = current_user.username if current_user.is_authenticated else 'unknown'
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT username, role, last_login FROM users ORDER BY username")
            users = c.fetchall()
            logger.debug(f"User {username} fetched {len(users)} users from database")
            return users
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} fetching users: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='users',
            details=f"Database error fetching users: {str(e)}"
        )
        flash("Database error fetching users.", "danger")
        return []

@users_bp.route('/admin/users/edit/<username>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(username):
    current_username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {current_username} accessing /admin/users/edit/{username} route with method: {request.method}")
    
    if request.method == 'POST':
        new_role = request.form.get('role').strip()
        if new_role not in VALID_ROLES:
            logger.warning(f"User {current_username} failed to update role for '{username}': Invalid role '{new_role}'")
            log_audit_action(
                username=current_username,
                action='edit_user_failed',
                target='users',
                details=f"Failed to update role for {username}: Invalid role {new_role}"
            )
            flash(f"Invalid role selected.", "danger")
            return redirect(url_for('users.manage_users'))

        logger.debug(f"User {current_username} updating role for user '{username}' to '{new_role}'")
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
                if c.rowcount == 0:
                    logger.warning(f"User {current_username} failed to update role for '{username}': User not found")
                    log_audit_action(
                        username=current_username,
                        action='edit_user_failed',
                        target='users',
                        details=f"Failed to update role for {username}: User not found"
                    )
                    flash(f"User '{username}' not found.", "danger")
                else:
                    conn.commit()
                    logger.info(f"User {current_username} updated role for '{username}' to '{new_role}'")
                    log_audit_action(
                        username=current_username,
                        action='edit_user',
                        target='users',
                        details=f"Updated role for {username} to {new_role}"
                    )
                    flash(f"Role for '{username}' updated to '{new_role}'.", "success")
        except sqlite3.Error as e:
            logger.error(f"Database error for user {current_username} updating role for '{username}': {str(e)}")
            log_audit_action(
                username=current_username,
                action='error',
                target='users',
                details=f"Database error updating role for {username}: {str(e)}"
            )
            flash("Database error updating user role.", "danger")
        return redirect(url_for('users.manage_users'))

    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT username, role FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            if not user:
                logger.warning(f"User {current_username} failed to access user '{username}' for edit: Not found")
                log_audit_action(
                    username=current_username,
                    action='view_failed',
                    target='edit_user',
                    details=f"User {username} not found"
                )
                flash(f"User '{username}' not found.", "danger")
                return redirect(url_for('users.manage_users'))
            logger.debug(f"User {current_username} accessed edit page for user '{username}'")
            log_audit_action(
                username=current_username,
                action='view',
                target='edit_user',
                details=f"Accessed edit page for user {username}"
            )
    except sqlite3.Error as e:
        logger.error(f"Database error for user {current_username} fetching user '{username}': {str(e)}")
        log_audit_action(
            username=current_username,
            action='error',
            target='edit_user',
            details=f"Database error fetching user {username}: {str(e)}"
        )
        flash("Database error fetching user.", "danger")
        return redirect(url_for('users.manage_users'))

    return render_template('edit_user.html', user=user, valid_roles=VALID_ROLES)

@users_bp.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /profile/change_password route with method: {request.method}")

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not current_password or not new_password or not confirm_password:
            logger.warning(f"User {username} failed to change password: Missing fields")
            log_audit_action(
                username=username,
                action='change_password_failed',
                target='change_password',
                details='Missing required fields'
            )
            flash("All fields are required.", "danger")
            return render_template('change_password.html', MIN_PASSWORD_LENGTH=MIN_PASSWORD_LENGTH)

        if new_password != confirm_password:
            logger.warning(f"User {username} failed to change password: Passwords do not match")
            log_audit_action(
                username=username,
                action='change_password_failed',
                target='change_password',
                details='New passwords do not match'
            )
            flash("New passwords do not match.", "danger")
            return render_template('change_password.html', MIN_PASSWORD_LENGTH=MIN_PASSWORD_LENGTH)

        if len(new_password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"User {username} failed to change password: Password too short")
            log_audit_action(
                username=username,
                action='change_password_failed',
                target='change_password',
                details=f"New password too short (< {MIN_PASSWORD_LENGTH} characters)"
            )
            flash(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.", "danger")
            return render_template('change_password.html', MIN_PASSWORD_LENGTH=MIN_PASSWORD_LENGTH)

        try:
            with get_db() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ?", (username,))
                user = c.fetchone()

                if not user:
                    logger.warning(f"User {username} not found during password change")
                    log_audit_action(
                        username=username,
                        action='change_password_failed',
                        target='change_password',
                        details='User not found'
                    )
                    flash("User not found.", "danger")
                    return redirect(url_for('users.change_password'))

                if not check_password_hash(user['password'], current_password):
                    logger.warning(f"User {username} failed to change password: Incorrect current password")
                    log_audit_action(
                        username=username,
                        action='change_password_failed',
                        target='change_password',
                        details='Incorrect current password'
                    )
                    flash("Current password is incorrect.", "danger")
                    return render_template('change_password.html', MIN_PASSWORD_LENGTH=MIN_PASSWORD_LENGTH)

                hashed_new_password = generate_password_hash(new_password)
                c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_password, username))
                conn.commit()

                logger.info(f"User {username} changed password successfully")
                log_audit_action(
                    username=username,
                    action='change_password',
                    target='change_password',
                    details='Password changed successfully'
                )
                flash("Password changed successfully.", "success")
                return redirect(url_for('users.change_password'))

        except sqlite3.Error as e:
            logger.error(f"Database error for user {username} changing password: {str(e)}")
            log_audit_action(
                username=username,
                action='error',
                target='change_password',
                details=f"Database error changing password: {str(e)}"
            )
            flash("Database error changing password.", "danger")

    log_audit_action(
        username=username,
        action='view',
        target='change_password',
        details='Accessed change password page'
    )
    return render_template('change_password.html', MIN_PASSWORD_LENGTH=MIN_PASSWORD_LENGTH)

@users_bp.route('/admin/users/reset/<username>', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(username):
    current_username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {current_username} accessing /admin/users/reset/{username} route")
    
    new_password = generate_password_hash("temp1234")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
            if c.rowcount == 0:
                logger.warning(f"User {current_username} failed to reset password for '{username}': User not found")
                log_audit_action(
                    username=current_username,
                    action='reset_password_failed',
                    target='users',
                    details=f"Failed to reset password for {username}: User not found"
                )
                flash(f"User '{username}' not found.", "danger")
            else:
                conn.commit()
                logger.info(f"User {current_username} reset password for '{username}'")
                log_audit_action(
                    username=current_username,
                    action='reset_password',
                    target='users',
                    details=f"Reset password for {username}"
                )
                flash(f"Password for '{username}' reset to 'temp1234'.", "info")
    except sqlite3.Error as e:
        logger.error(f"Database error for user {current_username} resetting password for '{username}': {str(e)}")
        log_audit_action(
            username=current_username,
            action='error',
            target='users',
            details=f"Database error resetting password for {username}: {str(e)}"
        )
        flash("Database error resetting password.", "danger")
    return redirect(url_for('users.manage_users'))

@users_bp.route('/admin/users/delete/<username>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(username):
    current_username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {current_username} accessing /admin/users/delete/{username} route")
    
    if username == current_username:
        logger.warning(f"User {current_username} attempted to delete their own account")
        log_audit_action(
            username=current_username,
            action='delete_user_failed',
            target='users',
            details=f"Attempted to delete own account {username}"
        )
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('users.manage_users'))

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            if c.rowcount == 0:
                logger.warning(f"User {current_username} failed to delete user '{username}': User not found")
                log_audit_action(
                    username=current_username,
                    action='delete_user_failed',
                    target='users',
                    details=f"Failed to delete user {username}: User not found"
                )
                flash(f"User '{username}' not found.", "danger")
            else:
                conn.commit()
                logger.info(f"User {current_username} deleted user '{username}'")
                log_audit_action(
                    username=current_username,
                    action='delete_user',
                    target='users',
                    details=f"Deleted user {username}"
                )
                flash(f"User '{username}' deleted.", "warning")
    except sqlite3.Error as e:
        logger.error(f"Database error for user {current_username} deleting user '{username}': {str(e)}")
        log_audit_action(
            username=current_username,
            action='error',
            target='users',
            details=f"Database error deleting user {username}: {str(e)}"
        )
        flash("Database error deleting user.", "danger")
    return redirect(url_for('users.manage_users'))