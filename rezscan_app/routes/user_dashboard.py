# rezscan_app/routes/user_dashboard.py

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
import logging

user_dashboard_bp = Blueprint('user_dashboard', __name__, url_prefix='/dashboard')

logger = logging.getLogger(__name__)

@user_dashboard_bp.route('/', strict_slashes=False)
@login_required
def dashboard():
    logger.debug(f"Accessing user dashboard for role: {current_user.role}")

    role = current_user.role.lower()

    if role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    template_name = f"{role}_dashboard.html"

    try:
        stats = {}

        if role in ['officer', 'scheduling', 'viewer']:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM residents')
                total_residents = c.fetchone()[0]

                c.execute('SELECT COUNT(*) FROM scans WHERE DATE(timestamp) = DATE("now", "localtime")')
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

                stats = {
                    'total_residents': total_residents,
                    'scans_today': scans_today,
                    'checked_in': checked_in
                }

        logger.debug(f"Rendering {template_name} with stats: {stats}")
        return render_template(template_name, user=current_user, stats=stats)

    except Exception as e:
        logger.error(f"Dashboard template not found or error for role: {role} - {str(e)}")
        flash('Dashboard not available for your role yet.', 'warning')
        return render_template('404.html'), 404
