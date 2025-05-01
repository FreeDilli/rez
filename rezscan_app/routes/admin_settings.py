from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import role_required
import sqlite3

settings_bp = Blueprint('settings', __name__, url_prefix='/admin/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_settings():
    with get_db() as db:
        c = db.cursor()

        if request.method == 'POST':
            updates = []
            for full_key, value in request.form.items():
                if "|" in full_key:
                    category, key = full_key.split("|", 1)
                    updates.append((category, key, value))

            for category, key, value in updates:
                c.execute('''
                    INSERT INTO settings (category, key, value)
                    VALUES (?, ?, ?)
                    ON CONFLICT(category, key) DO UPDATE SET value = excluded.value
                ''', (category, key, value))

            db.commit()
            flash('Settings updated successfully.', 'success')
            return redirect(url_for('settings.manage_settings'))

        c.execute("SELECT category, key, value FROM settings ORDER BY category, key")
        settings = c.fetchall()

        grouped_settings = {}
        for row in settings:
            cat, key, val = row
            grouped_settings.setdefault(cat, []).append((key, val))

        return render_template('admin_settings.html', settings=grouped_settings)

