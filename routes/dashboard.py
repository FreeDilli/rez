from flask import Blueprint, render_template, request, redirect, url_for
from models.database import get_db
from routes.auth import login_required
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/admin/dashboard', strict_slashes=False)
@login_required
def dashboard():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.mdoc, MAX(s.timestamp) as latest_time
            FROM scans s
            GROUP BY s.mdoc
        ''')
        latest_scans = c.fetchall()
        checked_in = []
        for mdoc, latest_time in latest_scans:
            c.execute('''
                SELECT r.name, r.mdoc, r.unit, r.housing_unit, r.level, s.timestamp, s.location
                FROM scans s
                JOIN residents r ON s.mdoc = r.mdoc
                WHERE s.mdoc = ? AND s.timestamp = ? AND s.status = 'In'
            ''', (mdoc, latest_time))
            result = c.fetchone()
            if result:
                checked_in.append(result)
    return render_template('dashboard.html', data=checked_in)

@dashboard_bp.route('/check_out', methods=['POST'])
@login_required
def check_out():
    mdoc = request.form['mdoc']
    location = request.form['location']
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO scans (mdoc, timestamp, status, location) VALUES (?, ?, ?, ?)",
            (mdoc, current_timestamp, "Out", location)
        )
        conn.commit()
    
    return redirect(url_for('dashboard.dashboard'))