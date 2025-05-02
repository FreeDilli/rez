# rezscan_app/routes/scheduling/movement_upload.py

from flask import Blueprint, render_template, request, redirect, flash, session, url_for
from rezscan_app.routes.common.auth import login_required, role_required

movement_upload_bp = Blueprint('movement_upload', __name__, url_prefix='/admin/scheduling')

@movement_upload_bp.route('/upload_movement', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'scheduling')
def upload_movement():
    if request.method == 'POST':
        movement_text = request.form.get('movement_text', '')
        if not movement_text.strip():
            flash("Please paste OCR text before previewing.", "warning")
            return redirect(url_for('movement_upload.upload_movement'))

        session['movement_text'] = movement_text  # Save to session
        return redirect(url_for('movement_match.match_preview'))

    return render_template('upload_movement_preview.html', raw_text=session.get('movement_text', ''))
