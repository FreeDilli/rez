from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from rezscan_app.routes.common.auth import role_required
from rezscan_app.models.database import get_db
import logging

logger = logging.getLogger(__name__)

schedule_review_bp = Blueprint('schedule_review', __name__, url_prefix='/schedule')

@schedule_review_bp.route('/review', methods=['GET'])
@login_required
@role_required('admin', 'scheduling')
def review_matches():
    db = get_db()
    c = db.cursor()

    try:
        c.execute('''
            SELECT id, original_name, original_mdoc, original_housing_unit,
                   suggested_name, suggested_mdoc, suggested_housing_unit,
                   block_title, block_time, source_text
            FROM schedule_match_review
            ORDER BY block_time ASC
        ''')
        rows = c.fetchall()
    except Exception as e:
        logger.error(f"Error fetching schedule match review items: {str(e)}")
        flash("Error loading match review data.", "danger")
        rows = []

    return render_template('schedule/schedule_match_review.html', matches=rows)


@schedule_review_bp.route('/review/<int:match_id>/approve', methods=['POST'])
@login_required
@role_required('admin', 'scheduling')
def approve_match(match_id):
    db = get_db()
    c = db.cursor()

    try:
        # Get suggested values
        c.execute('''
            SELECT suggested_mdoc, block_title FROM schedule_match_review WHERE id = ?
        ''', (match_id,))
        row = c.fetchone()
        if not row:
            flash("Match not found.", "warning")
            return redirect(url_for('schedule_review.review_matches'))

        mdoc, block_title = row['suggested_mdoc'], row['block_title']

        # Find group by block_title (must be exact match for now)
        c.execute('SELECT id FROM schedule_groups WHERE name = ?', (block_title,))
        group = c.fetchone()
        if not group:
            flash(f"No matching schedule group found for '{block_title}'.", "danger")
            return redirect(url_for('schedule_review.review_matches'))

        group_id = group['id']

        # Insert assignment (avoid duplicate)
        c.execute('''
            INSERT OR IGNORE INTO resident_schedules (mdoc, group_id)
            VALUES (?, ?)
        ''', (mdoc, group_id))

        # Remove the review entry
        c.execute('DELETE FROM schedule_match_review WHERE id = ?', (match_id,))
        db.commit()
        flash("Match approved and assigned.", "success")
    except Exception as e:
        db.rollback()
        logger.error(f"Error approving match: {str(e)}")
        flash("Failed to approve match.", "danger")

    return redirect(url_for('schedule_review.review_matches'))


@schedule_review_bp.route('/review/<int:match_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'scheduling')
def delete_match(match_id):
    db = get_db()
    c = db.cursor()
    try:
        c.execute('DELETE FROM schedule_match_review WHERE id = ?', (match_id,))
        db.commit()
        flash("Match deleted.", "info")
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting match: {str(e)}")
        flash("Failed to delete match.", "danger")

    return redirect(url_for('schedule_review.review_matches'))
