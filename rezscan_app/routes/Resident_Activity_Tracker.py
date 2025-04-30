from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from datetime import datetime
import logging

resident_activity_tracker_bp = Blueprint('resident_activity_tracker', __name__)
logger = logging.getLogger(__name__)

@resident_activity_tracker_bp.route('/live', strict_slashes=False)
@login_required
def live_dashboard():
    logger.debug(f"User {current_user.username} accessing Resident Activity Tracker")
    
    checked_in = []
    try:
        with get_db() as conn:
            c = conn.cursor()

            # Log audit entry for dashboard access
            c.execute("""
                INSERT INTO audit_log (username, action, target, details)
                VALUES (?, ?, ?, ?)
            """, (
                current_user.username,
                'view_dashboard',
                'resident_activity_tracker',
                'Accessed resident activity dashboard'
            ))

            # Fetch latest scan for each resident with name
            c.execute('''
                SELECT s.mdoc, MAX(s.timestamp) AS latest_time, r.name
                FROM scans s
                LEFT JOIN residents r ON s.mdoc = r.mdoc
                GROUP BY s.mdoc
            ''')
            latest_scans = c.fetchall()
            logger.debug(f"Retrieved {len(latest_scans)} latest scans")

            for mdoc, latest_time, name in latest_scans:
                c.execute('''
                    SELECT r.name, s.mdoc, r.unit, r.housing_unit, r.level, s.timestamp, s.location
                    FROM scans s
                    LEFT JOIN residents r ON s.mdoc = r.mdoc
                    WHERE s.mdoc = ? AND s.timestamp = ? AND s.status = 'In'
                ''', (mdoc, latest_time))
                result = c.fetchone()
                if result:
                    checked_in.append(result)
            
            logger.info(f"User {current_user.username} successfully loaded {len(checked_in)} checked-in residents")

            conn.commit()

    except Exception as e:
        logger.error(f"Error retrieving resident activity for user {current_user.username}: {str(e)}", exc_info=True)
        flash("Error loading resident activity.", "danger")
        
        # Log error to audit log
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO audit_log (username, action, target, details)
                    VALUES (?, ?, ?, ?)
                """, (
                    current_user.username,
                    'view_dashboard_failed',
                    'resident_activity_tracker',
                    f'Failed to load resident activity: {str(e)}'
                ))
                conn.commit()
        except Exception as audit_error:
            logger.error(f"Failed to write audit log for dashboard error: {str(audit_error)}")

    return render_template('resident_activity_tracker.html', data=checked_in)

@resident_activity_tracker_bp.route('/check_out', methods=['POST'])
@login_required
def check_out():
    mdoc = request.form.get('mdoc')
    location = request.form.get('location')
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Fetch resident name
    resident_name = None
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM residents WHERE mdoc = ?", (mdoc,))
            result = c.fetchone()
            if result:
                resident_name = result[0]
            else:
                logger.warning(f"No resident found for mdoc {mdoc}")
                resident_name = "Unknown Resident"
    except Exception as e:
        logger.error(f"Error fetching resident name for mdoc {mdoc}: {str(e)}")
        resident_name = "Unknown Resident"

    logger.info(f"User {current_user.username} attempting to check out resident {resident_name} from {location}")

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO scans (mdoc, timestamp, status, location) VALUES (?, ?, ?, ?)",
                (mdoc, current_timestamp, "Out", location)
            )
            
            # Log audit entry for check-out
            c.execute("""
                INSERT INTO audit_log (username, action, target, details)
                VALUES (?, ?, ?, ?)
            """, (
                current_user.username,
                'check_out',
                f'resident:{resident_name}',
                f'Checked out resident from {location}'
            ))

            conn.commit()

            logger.info(f"User {current_user.username} successfully checked out resident {resident_name} from {location}")
            flash(f"Resident {resident_name} checked out successfully.", "success")

    except Exception as e:
        logger.error(f"Error during check out for resident {resident_name} by user {current_user.username}: {str(e)}", exc_info=True)
        flash(f"Failed to check out resident {resident_name}.", "danger")
        
        # Log error to audit log
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO audit_log (username, action, target, details)
                    VALUES (?, ?, ?, ?)
                """, (
                    current_user.username,
                    'check_out_failed',
                    f'resident:{resident_name}',
                    f'Failed to check out resident from {location}: {str(e)}'
                ))
                conn.commit()
        except Exception as audit_error:
            logger.error(f"Failed to write audit log for check-out error: {str(audit_error)}")

    return redirect(url_for('resident_activity_tracker.live_dashboard'))