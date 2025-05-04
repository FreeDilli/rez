from flask import Blueprint, render_template
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
from rezscan_app.models.database import get_db

schedule_match_review_bp = Blueprint('schedule_match_review', __name__)

@schedule_match_review_bp.route('/schedule/review_matches')
@login_required
@role_required('admin', 'scheduling')
def review_matches():
    db = get_db()
    c = db.cursor()

    c.execute('''
        SELECT id, block_title, block_time, source_line,
               suggested_name, suggested_mdoc, suggested_housing,
               status, reviewed_by, reviewed_at, created_at
        FROM schedule_match_review
        ORDER BY created_at DESC
    ''')

    reviews = c.fetchall()

    return render_template('schedule/review_matches.html', reviews=reviews)
