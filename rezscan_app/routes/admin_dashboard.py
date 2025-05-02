from flask import Blueprint, render_template
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required, role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin', strict_slashes=False)
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db()
    c = db.cursor()

    c.execute("SELECT COUNT(*) FROM residents")
    total_residents = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM scans WHERE strftime('%Y-%m-%d', timestamp) = strftime('%Y-%m-%d', 'now', 'localtime')")
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

    c.execute("SELECT COUNT(*) FROM users where role = 'admin'")
    total_admins = c.fetchone()[0]

    stats = {
        'total_residents': total_residents,
        'scans_today': scans_today,
        'checked_in': checked_in,
        'total_users': total_users
    }

    return render_template('admin_dashboard.html', stats=stats)