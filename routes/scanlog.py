from flask import Blueprint, render_template
from models.database import get_db
from routes.auth import login_required

scanlog_bp = Blueprint('scanlog', __name__)

@scanlog_bp.route('/admin/scanlog', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def scanlog():
    try:
        db = get_db()
        c = db.cursor()
        c.execute('SELECT * FROM scans_with_residents ORDER BY time desc')
        data = c.fetchall()
        c.execute('SELECT DISTINCT status FROM scans_with_residents ORDER BY status')
        status_options = [row[0] for row in c.fetchall() if row[0]]
        c.execute('SELECT DISTINCT location FROM scans_with_residents ORDER BY location')
        location_options = [row[0] for row in c.fetchall() if row[0]]
        return render_template('scanlog.html', scans=data, status_options=status_options, location_options=location_options)
    except Exception as e:
        return f"Database error: {str(e)}", 500