from flask import Blueprint, render_template
from models.database import get_db
from routes.auth import login_required, role_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin', strict_slashes=False)
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db()
    c = db.cursor()

    c.execute("SELECT COUNT(*) FROM residents")
    total_residents = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM scans WHERE DATE(timestamp) = date('now')")
    active_today = c.fetchone()[0]

    stats = {
        'total_residents': total_residents,
        'active_today': active_today
    }

    return render_template('admin_dashboard.html', stats=stats)