from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from werkzeug.security import generate_password_hash
from rezscan_app.utils.constants import VALID_ROLES, MIN_PASSWORD_LENGTH
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.audit_logging import log_audit_action
import logging
import sqlite3
import secrets
import re

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__)

@users_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_users():
    username = current_user.username
    logger.debug(f"User {username} accessing /admin/users route with method: {request.method}")
    
    if request.method == 'POST':
        action = request.form.get('action')
        target_username = request.form.get('username').strip()
        role = request.form.get('role').strip()

        if not re.match(r'^[a-zA-Z0-9_]{1,50}$', target_username):
            logger.warning(f"User {username} provided invalid username: {target_username}")
            log_audit_action(username, 'add_user_failed', 'users', f"Invalid username format: {target_username}")
            flash("Username must be alphanumeric and up to 50 characters.", "warning")
            return render_template('admin/users.html', users=get_users(), valid_roles=VALID_ROLES)

        logger.debug(f"User {username} processing action '{action}' for username: {target_username}, role: {role}")

        if action == 'add':
            password = request.form.get('password').strip()
            if len(password) < MIN_PASSWORD_LENGTH:
                logger.warning(f"User {username} failed to add user '{target_username}': Password too short")
                log_audit_action(username, 'add_user_failed', 'users', f"Password too short for {target_username}")
                flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "warning")
                return render_template('admin/users.html', users=get_users(), valid_roles=VALID_ROLES)
            if role not in VALID_ROLES:
                logger.warning(f"User {username} failed to add user '{target_username}': Invalid role '{role}'")
                log_audit_action(username, 'add_user_failed', 'users', f"Invalid role {role} for {target_username}")
                flash("Invalid role selected.", "warning")
                return render_template('admin/users.html', users=get_users(), valid_roles=VALID_ROLES)
            
            hashed_password = generate_password_hash(password)
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (target_username, hashed_password, role))
                    conn.commit()
                    logger.info(f"User {username} added user '{target_username}' with role '{role}'")
                    log_audit_action(username, 'add_user', 'users', f"Added user {target_username} with role {role}")
                    flash(f"User '{target_username}' added successfully.", "success")
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: users.username" in str(e):
                    logger.warning(f"User {username} failed to add user '{target_username}': Username exists")
                    log_audit_action(username, 'add_user_failed', 'users', f"Username {target_username} exists")
                    flash(f"User '{target_username}' already exists.", "warning")
                else:
                    logger.error(f"User {username} failed to add user '{target_username}': {str(e)}")
                    log_audit_action(username, 'error', 'users', f"Database error adding {target_username}: {str(e)}")
                    flash("Database error adding user.", "danger")
            except sqlite3.Error as e:
                logger.error(f"User {username} failed to add user '{target_username}': {str(e)}")
                log_audit_action(username, 'error', 'users', f"Database error adding {target_username}: {str(e)}")
                flash("Database error adding user.", "danger")
    else:
        log_audit_action(username, 'view', 'users', 'Viewed users management page')
        logger.info(f"User {username} viewed users management page")

    users = get_users()
    logger.debug(f"User {username} fetched {len(users)} users")
    return render_template('admin/users.html', users=users, valid_roles=VALID_ROLES)

def get_users():
    username = current_user.username
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT username, role, last_login FROM users ORDER BY username")
            rows = c.fetchall()
            users = []
            for row in rows:
                last_login = row['last_login']
                users.append({
                    'username': row['username'],
                    'role': row['role'],
                    'last_login': last_login
                })
            logger.debug(f"User {username} fetched {len(users)} users from database")
            return users
    except sqlite3.Error as e:
        logger.error(f"User {username} failed to fetch users: {str(e)}")
        log_audit_action(username, 'error', 'users', f"Database error fetching users: {str(e)}")
        flash("Database error fetching users.", "danger")
        return []

@users_bp.route('/admin/users/edit/<username>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(username):
    current_username = current_user.username
    logger.debug(f"User {current_username} accessing /admin/users/edit/{username} route with method: {request.method}")
    
    if request.method == 'POST':
        new_role = request.form.get('role').strip()
        if new_role not in VALID_ROLES:
            logger.warning(f"User {current_username} failed to update role for '{username}': Invalid role '{new_role}'")
            log_audit_action(current_username, 'edit_user_failed', 'users', f"Invalid role {new_role}")
            flash("Invalid role selected.", "warning")
            return redirect(url_for('users.manage_users'))

        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
                if c.rowcount == 0:
                    logger.warning(f"User {current_username} failed to update role for '{username}': User not found")
                    log_audit_action(current_username, 'edit_user_failed', 'users', f"User {username} not found")
                    flash(f"User '{username}' not found.", "warning")
                else:
                    conn.commit()
                    logger.info(f"User {current_username} updated role for '{username}' to '{new_role}'")
                    log_audit_action(current_username, 'edit_user', 'users', f"Updated role for {username} to {new_role}")
                    flash(f"Role for '{username}' updated to '{new_role}'.", "success")
        except sqlite3.Error as e:
            logger.error(f"User {current_username} failed to update role for '{username}': {str(e)}")
            log_audit_action(current_username, 'error', 'users', f"Database error updating {username}: {str(e)}")
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
                log_audit_action(current_username, 'view_failed', 'edit_user', f"User {username} not found")
                flash(f"User '{username}' not found.", "warning")
                return redirect(url_for('users.manage_users'))
            logger.info(f"User {current_username} accessed edit page for user '{username}'")
            log_audit_action(current_username, 'view', 'edit_user', f"Accessed edit page for user {username}")
    except sqlite3.Error as e:
        logger.error(f"User {current_username} failed to fetch user '{username}': {str(e)}")
        log_audit_action(current_username, 'error', 'edit_user', f"Database error fetching {username}: {str(e)}")
        flash("Database error fetching user.", "danger")
        return redirect(url_for('users.manage_users'))

    return render_template('admin/edit_user.html', user=user, valid_roles=VALID_ROLES)

@users_bp.route('/admin/users/reset/<username>', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(username):
    current_username = current_user.username
    logger.debug(f"User {current_username} accessing /admin/users/reset/{username} route")
    
    new_password = secrets.token_urlsafe(12)
    hashed_password = generate_password_hash(new_password)
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
            if c.rowcount == 0:
                logger.warning(f"User {current_username} failed to reset password for '{username}': User not found")
                log_audit_action(current_username, 'reset_password_failed', 'users', f"User {username} not found")
                flash(f"User '{username}' not found.", "warning")
            else:
                conn.commit()
                logger.info(f"User {current_username} reset password for '{username}'")
                log_audit_action(current_username, 'reset_password', 'users', f"Reset password for {username}")
                flash(f"Password for '{username}' reset to '{new_password}'.", "info")
    except sqlite3.Error as e:
        logger.error(f"User {current_username} failed to reset password for '{username}': {str(e)}")
        log_audit_action(current_username, 'error', 'users', f"Database error resetting {username}: {str(e)}")
        flash("Database error resetting password.", "danger")
    return redirect(url_for('users.manage_users'))

@users_bp.route('/admin/users/delete/<username>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(username):
    current_username = current_user.username
    logger.debug(f"User {current_username} accessing /admin/users/delete/{username} route")
    
    if username == current_username:
        logger.warning(f"User {current_username} attempted to delete their own account")
        log_audit_action(current_username, 'delete_user_failed', 'users', f"Attempted to delete own account {username}")
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for('users.manage_users'))

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            if c.rowcount == 0:
                logger.warning(f"User {current_username} failed to delete user '{username}': User not found")
                log_audit_action(current_username, 'delete_user_failed', 'users', f"User {username} not found")
                flash(f"User '{username}' not found.", "warning")
            else:
                conn.commit()
                logger.info(f"User {current_username} deleted user '{username}'")
                log_audit_action(current_username, 'delete_user', 'users', f"Deleted user {username}")
                flash(f"User '{username}' deleted.", "warning")
    except sqlite3.Error as e:
        logger.error(f"User {current_username} failed to delete user '{username}': {str(e)}")
        log_audit_action(current_username, 'error', 'users', f"Database error deleting {username}: {str(e)}")
        flash("Database error deleting user.", "danger")
    return redirect(url_for('users.manage_users'))