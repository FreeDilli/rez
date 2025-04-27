from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from rezscan_app.models.database import get_db
from datetime import datetime
import logging

resident_activity_tracker_bp = Blueprint('resident_activity_tracker', __name__, url_prefix='/live')

logger = logging.getLogger(__name__)

@resident_activity_tracker_bp.route('/', strict_slashes=False)
@login_required
def live_dashboard():
    logger.debug("Accessing Resident Activity Tracker")

    checked_in = []
    try:
        with get_db() as conn:
            c = conn.cursor()

            # Fetch latest scan for each resident
            c.execute('''
                SELECT s.mdoc, MAX(s.timestamp) AS latest_time
                FROM scans s
                GROUP BY s.mdoc
            ''')
            latest_scans = c.fetchall()

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

    except Exception as e:
        logger.error(f"Error retrieving resident activity: {e}")
        flash("Error loading resident activity.", "danger")

    return render_template('resident_activity_tracker.html', data=checked_in)

@resident_activity_tracker_bp.route('/check_out', methods=['POST'])
@login_required
def check_out():
    mdoc = request.form.get('mdoc')
    location = request.form.get('location')
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO scans (mdoc, timestamp, status, location) VALUES (?, ?, ?, ?)",
                (mdoc, current_timestamp, "Out", location)
            )
            conn.commit()

            logger.info(f"Resident {mdoc} checked out from {location}")

    except Exception as e:
        logger.error(f"Error during check out: {e}")
        flash("Failed to check out resident.", "danger")

    return redirect(url_for('resident_activity_tracker.live_dashboard'))
