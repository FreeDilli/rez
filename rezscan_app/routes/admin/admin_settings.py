from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.audit_logging import log_audit_action
import sqlite3
import logging
import re

logger = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__, url_prefix='/admin/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_settings():
    username = current_user.username
    logger.debug(f"User {username} accessing /admin/settings, method: {request.method}")
    
    with get_db() as db:
        c = db.cursor()

        if request.method == 'POST':
            updates = []
            for full_key, value in request.form.items():
                if "|" in full_key:
                    category, key = full_key.split("|", 1)
                    if not (re.match(r'^[a-zA-Z0-9_]+$', category) and re.match(r'^[a-zA-Z0-9_]+$', key)):
                        logger.warning(f"User {username} attempted invalid setting update: {category}|{key}")
                        flash("Invalid category or key format.", "warning")
                        continue
                    updates.append((category, key, value))

            try:
                for category, key, value in updates:
                    c.execute('''
                        INSERT INTO settings (category, key, value)
                        VALUES (?, ?, ?)
                        ON CONFLICT(category, key) DO UPDATE SET value = excluded.value
                    ''', (category, key, value))
                db.commit()
                flash('Settings updated successfully.', 'success')
                log_audit_action(username, 'update_settings', 'settings', f"Updated {len(updates)} settings")
                logger.info(f"User {username} updated {len(updates)} settings")
            except sqlite3.Error as e:
                logger.error(f"User {username} failed to update settings: {str(e)}")
                log_audit_action(username, 'update_settings_failed', 'settings', f"Database error: {str(e)}")
                flash("Database error updating settings.", "danger")
            
            return redirect(url_for('settings.manage_settings'))

        try:
            c.execute("SELECT category, key, value FROM settings ORDER BY category, key")
            settings = c.fetchall()
            log_audit_action(username, 'view', 'settings', "Viewed settings page")
            logger.debug(f"User {username} fetched settings")
        except sqlite3.Error as e:
            logger.error(f"User {username} failed to fetch settings: {str(e)}")
            log_audit_action(username, 'error', 'settings', f"Database error: {str(e)}")
            flash("Database error fetching settings.", "danger")
            settings = []

        grouped_settings = {}
        for row in settings:
            cat, key, val = row
            grouped_settings.setdefault(cat, []).append((key, val))

        return render_template('admin/admin_settings.html', settings=grouped_settings)