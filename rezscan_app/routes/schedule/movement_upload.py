from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required

schedules_bp = Blueprint('schedules', __name__)

@schedules_bp.route('/schedule/upload_movement', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'scheduling')
def upload_movement():
    if request.method == 'POST':
        raw_text = request.form.get('movement_text', '')
        if len(raw_text) > 3000:
            flash("Input was too large. Truncated for preview.", "warning")
            raw_text = raw_text[:3000]
        session['movement_text'] = raw_text
        return redirect(url_for('schedules.match_preview'))

    return redirect(url_for('movement_match.match_preview'))


