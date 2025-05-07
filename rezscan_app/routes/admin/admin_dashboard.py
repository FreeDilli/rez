from flask import Blueprint, render_template, flash
from rezscan_app.models.database import get_db
from flask_login import login_required, current_user
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.audit_logging import log_audit_action
import sqlite3
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin', strict_slashes=False)
@login_required
@role_required('admin')
def admin_dashboard():
    username = current_user.username
    logger.debug(f"User {username} accessed admin dashboard")
    
    try:
        db = get_db()
        c = db.cursor()

        c.execute("SELECT COUNT(*) FROM residents")
        total_residents = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM scans WHERE DATE(timestamp) = DATE('now', 'localtime')")
        scans_today = c.fetchone()[0]

        c.execute('''
            SELECT COUNT(*)
            FROM (
                SELECT mdoc, MAX(timestamp) AS latest_time
                FROM scans
                GROUP BY mdoc
                HAVING (SELECT status FROM scans WHERE mdoc = scans.mdoc AND timestamp = latest_time) = 'In'
            )
        ''')
        checked_in = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        total_admins = c.fetchone()[0]

        c.execute('''
                SELECT location, COUNT(*) as scan_count
                FROM scans
                WHERE location IS NOT NULL
                GROUP BY location
                ORDER BY scan_count DESC
                LIMIT 1
        ''')
        result = c.fetchone()
        top_location = result[0] if result else None

        stats = {
            'total_residents': total_residents,
            'scans_today': scans_today,
            'checked_in': checked_in,
            'total_users': total_users,
            'top_location': top_location
        }

        # log_audit_action(username, 'view', 'admin_dashboard', f"Viewed dashboard with stats: {stats}")
        log_audit_action(username, 'view', 'admin_dashboard', "Viewed admin dashboard")
        logger.info(f"User {username} viewed admin dashboard")
        return render_template('admin/admin_dashboard.html', stats=stats)
    
    except sqlite3.Error as e:
        logger.error(f"User {username} encountered database error in admin dashboard: {str(e)}")
        log_audit_action(username, 'error', 'admin_dashboard', f"Database error: {str(e)}")
        flash("Database error loading dashboard.", "danger")
        return render_template('admin/admin_dashboard.html', stats={})