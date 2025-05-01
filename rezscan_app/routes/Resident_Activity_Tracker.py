from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from datetime import datetime
import logging
import pandas as pd

resident_activity_tracker_bp = Blueprint('resident_activity_tracker', __name__)
logger = logging.getLogger(__name__)

@resident_activity_tracker_bp.route('/live', strict_slashes=False)
@login_required
def live_dashboard():
    logger.debug(f"User {current_user.username} accessing Resident Activity Tracker")
    
    # Get sorting parameters
    sort = request.args.get('sort', 'timestamp')
    direction = request.args.get('direction', 'desc')  # Changed default from 'asc' to 'desc'
    
    # Validate sort and direction
    valid_sorts = ['name', 'timestamp']
    sort = sort if sort in valid_sorts else 'timestamp'
    direction = direction if direction in ['asc', 'desc'] else 'desc'  # Changed default from 'asc' to 'desc'
    
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
                'view',
                'resident_activity_tracker',
                f'Accessed resident activity dashboard with sort={sort}, direction={direction}'
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
            
            # Sort the checked_in list
            if sort == 'name':
                checked_in.sort(key=lambda x: (x[0] or 'Unknown Resident').lower(), reverse=(direction == 'desc'))
            elif sort == 'timestamp':
                checked_in.sort(key=lambda x: x[5], reverse=(direction == 'desc'))

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
                    'view_failed',
                    'resident_activity_tracker',
                    f'Failed to load resident activity: {str(e)}'
                ))
                conn.commit()
        except Exception as audit_error:
            logger.error(f"Failed to write audit log for dashboard error: {str(audit_error)}")

    return render_template('resident_activity_tracker.html', data=checked_in, sort=sort, direction=direction)

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

# ... (previous routes: /live, /check_out, /heatmap-data remain unchanged)

@resident_activity_tracker_bp.route('/heatmap-data', methods=['GET'])
@login_required
def heatmap_data():
    logger.debug(f"User {current_user.username} accessing heatmap data")
    
    date_filter = request.args.get('date_filter', '1 day')
    
    try:
        with get_db() as conn:
            c = conn.cursor()

            # Log audit entry for heatmap access
            c.execute("""
                INSERT INTO audit_log (username, action, target, details)
                VALUES (?, ?, ?, ?)
            """, (
                current_user.username,
                'view',
                'heatmap',
                f'Accessed resident activity heatmap data with date_filter={date_filter}'
            ))

            # Fetch latest scan for each resident with status = 'In'
            c.execute('''
                SELECT s.mdoc, MAX(s.timestamp) AS latest_time, r.name, r.unit, r.housing_unit, r.level, s.location
                FROM scans s
                LEFT JOIN residents r ON s.mdoc = r.mdoc
                WHERE s.status = 'In' AND s.timestamp >= datetime('now', ?)
                GROUP BY s.mdoc
            ''', (f'-{date_filter}',))
            data = c.fetchall()

            if not data:
                logger.warning("No checked-in residents found for heatmap")
                return jsonify({
                    'locations': [],
                    'time_buckets': [],
                    'values': []
                })

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['mdoc', 'latest_time', 'name', 'unit', 'housing_unit', 'level', 'location'])
            df['timestamp'] = pd.to_datetime(df['latest_time'])

            # Create hourly time buckets
            df['time_bucket'] = df['timestamp'].dt.floor('H').dt.strftime('%Y-%m-%d %H:%00')

            # Group by location and time_bucket, count residents
            heatmap_data = df.groupby(['location', 'time_bucket']).size().unstack(fill_value=0)

            # Prepare data for Plotly
            locations = heatmap_data.index.tolist()
            time_buckets = heatmap_data.columns.tolist()
            values = heatmap_data.values.tolist()

            logger.info(f"User {current_user.username} successfully loaded heatmap data with {len(locations)} locations and {len(time_buckets)} time buckets")

            conn.commit()

            return jsonify({
                'locations': locations,
                'time_buckets': time_buckets,
                'values': values
            })

    except Exception as e:
        logger.error(f"Error generating heatmap data for user {current_user.username}: {str(e)}", exc_info=True)
        
        # Log error to audit log
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO audit_log (username, action, target, details)
                    VALUES (?, ?, ?, ?)
                """, (
                    current_user.username,
                    'view_failed',
                    'heatmap',
                    f'Failed to load heatmap data: {str(e)}'
                ))
                conn.commit()
        except Exception as audit_error:
            logger.error(f"Failed to write audit log for heatmap error: {str(audit_error)}")

        return jsonify({'error': 'Failed to generate heatmap data'}), 500

@resident_activity_tracker_bp.route('/heatmap', methods=['GET'])
@login_required
def heatmap():
    logger.debug(f"User {current_user.username} accessing heatmap page")
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO audit_log (username, action, target, details)
                VALUES (?, ?, ?, ?)
            """, (
                current_user.username,
                'view',
                'heatmap_page',
                'Accessed resident activity heatmap page'
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log for heatmap page access: {str(e)}")
    return render_template('heatmap.html')