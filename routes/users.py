from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
from config import Config
from werkzeug.security import generate_password_hash

users_bp = Blueprint('users', __name__)
DB_PATH = Config.DB_PATH

@users_bp.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    message = None

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').strip()
        role = request.form.get('role').strip()

        if action == 'add':
            password = request.form.get('password').strip()
            hashed_password = generate_password_hash(password)
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
                    conn.commit()
                    flash(f"User '{username}' added successfully.", "success")
            except sqlite3.IntegrityError:
                flash(f"User '{username}' already exists.", "danger")

    # Fetch current users
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row  # 🟢 Enables dict-like access
        c = conn.cursor()
        c.execute("SELECT username, role FROM users ORDER BY username")
        users = c.fetchall()

    return render_template('users.html', users=users)

@users_bp.route('/admin/users/reset/<username>', methods=['POST'])
def reset_password(username):
    new_password = generate_password_hash("temp1234")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        flash(f"Password for '{username}' reset to 'temp1234'.", "info")
    return redirect(url_for('users.manage_users'))

@users_bp.route('/admin/users/delete/<username>', methods=['POST'])
def delete_user(username):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        flash(f"User '{username}' deleted.", "warning")
    return redirect(url_for('users.manage_users'))

