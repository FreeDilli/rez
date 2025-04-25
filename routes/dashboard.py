from flask import Blueprint, render_template
from models.database import get_db
from routes.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/admin/dashboard', strict_slashes=False)
@login_required
def dashboard():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.mdoc, MAX(s.date || ' ' || s.time) as latest_time
            FROM scans s
            GROUP BY s.mdoc
        ''')
        latest_scans = c.fetchall()
        checked_in = []
        for mdoc, latest_time in latest_scans:
            c.execute('''
                SELECT r.name, r.mdoc, r.unit, r.housing_unit, r.level, s.date, s.time, s.location
                FROM scans s
                JOIN residents r ON s.mdoc = r.mdoc
                WHERE s.mdoc = ? AND (s.date || ' ' || s.time) = ? AND s.status = 'In'
            ''', (mdoc, latest_time))
            result = c.fetchone()
            if result:
                checked_in.append(result)
    return render_template('dashboard.html', data=checked_in)