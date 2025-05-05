from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
from rezscan_app.models.database import get_db
import os
import logging

logger = logging.getLogger(__name__)

mvmt_schedules_bp = Blueprint('mvmt_schedules', __name__)

@mvmt_schedules_bp.route('/schedule/upload_movement', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'scheduling')
def upload_movement():
    if request.method == 'POST':
        uploaded_file = request.files.get('pdf_file')
        if not uploaded_file or not uploaded_file.filename.endswith('.pdf'):
            flash("Please upload a valid PDF file.", "warning")
            return redirect(request.url)

        temp_path = os.path.join('tmp', uploaded_file.filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        uploaded_file.save(temp_path)

        try:
            from rezscan_app.utils.schedule_parser import parse_schedule_blocks
            parsed_blocks = parse_schedule_blocks(temp_path)

            if not parsed_blocks:
                flash("No schedule blocks found in the PDF.", "warning")
                return redirect(request.url)

            # Save raw text to session and redirect to preview route
            raw_text = "\n".join(
                f"{block['time'] or 'Block'} - {block['title']}\n" + "\n".join(block['residents'])
                for block in parsed_blocks
            )
            session['movement_text'] = raw_text
            flash("PDF successfully parsed. Ready to review and confirm.", "success")
            return redirect(url_for('movement_match.match_preview'))

        except Exception as e:
            logger.error(f"Error processing schedule PDF: {e}", exc_info=True)
            flash("Failed to process the schedule file.", "danger")
            return redirect(request.url)

    return render_template("schedule/upload_movement_preview.html")
