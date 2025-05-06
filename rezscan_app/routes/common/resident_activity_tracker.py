from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from datetime import datetime
import logging
import pandas as pd
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rezscan_app.config import Config
from rezscan_app.utils.audit_logging import log_audit_action
import pytz

resident_activity_tracker_bp = Blueprint('resident_activity_tracker', __name__)
logger = logging.getLogger(__name__)

# Initialize Limiter (configured in app.py)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def user_key_func():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

@resident_activity_tracker_bp.route('/live', strict_slashes=False)
@login_required
def live_dashboard():
    logger.debug(f"User {current_user.username} accessing Resident Activity Tracker")
    
    sort = request.args.get('sort', 'timestamp')
    direction = request.args.get('direction', 'desc')
    view_type = request.args.get('view_type', 'Location')  # Building or Location
    
    # Set default selected_view based on view_type
    default_selected_view = 'All Locations' if view_type == 'Location' else 'All Buildings'
    selected_view = request.args.get('view', default_selected_view)
    
    # Get user's default_view from users table
    default_view = 'All Locations'
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT default_view FROM users WHERE username = ?", (current_user.username,))
            result = c.fetchone()
            if result and result[0]:
                default_view = result[0]
    except Exception as e:
        logger.error(f"Error fetching default_view for user {current_user.username}: {str(e)}")
    
    # Ensure selected_view is valid for the current view_type
    checked_in = []
    locations = []
    buildings = []
    try:
        with get_db() as conn:
            c = conn.cursor()
            # Get all locations and buildings
            c.execute('SELECT name, bldg FROM locations ORDER BY name')
            location_data = c.fetchall()
            locations = [row[0] for row in location_data]
            buildings = sorted(list(set(row[1] for row in location_data)))

            # Validate selected_view
            if view_type == 'Location' and selected_view not in ['All Locations'] + locations:
                selected_view = 'All Locations'
            elif view_type == 'Building' and selected_view not in ['All Buildings'] + buildings:
                selected_view = 'All Buildings'

            log_audit_action(
                username=current_user.username,
                action='view',
                target='resident_activity_tracker',
                details=f'Accessed resident activity dashboard with sort={sort}, direction={direction}, view_type={view_type}, view={selected_view}'
            )

            # Get latest scans
            c.execute('''
                SELECT s.mdoc, MAX(s.timestamp) AS latest_time, r.name
                FROM scans s
                LEFT JOIN residents r ON s.mdoc = r.mdoc
                GROUP BY s.mdoc
            ''')
            latest_scans = c.fetchall()
            logger.debug(f"Retrieved {len(latest_scans)} latest scans")

            for mdoc, latest_time, name in latest_scans:
                query = '''
                    SELECT r.name, s.mdoc, r.unit, r.housing_unit, r.level, s.timestamp, s.location, l.bldg
                    FROM scans s
                    LEFT JOIN residents r ON s.mdoc = r.mdoc
                    LEFT JOIN locations l ON s.location = l.name
                    WHERE s.mdoc = ? AND s.timestamp = ? AND s.status = 'In'
                '''
                params = (mdoc, latest_time)
                if view_type == 'Location' and selected_view != 'All Locations':
                    query += ' AND s.location = ?'
                    params += (selected_view,)
                elif view_type == 'Building' and selected_view != 'All Buildings':
                    query += ' AND l.bldg = ?'
                    params += (selected_view,)
                c.execute(query, params)
                result = c.fetchone()
                if result:
                    checked_in.append(result)
            
            logger.debug(f"Filtered to {len(checked_in)} checked-in residents for view_type={view_type}, selected_view={selected_view}")

            valid_sorts = ['name', 'timestamp']
            sort = sort if sort in valid_sorts else 'timestamp'
            direction = direction if direction in ['asc', 'desc'] else 'desc'

            if sort == 'name':
                checked_in.sort(key=lambda x: (x[0] or 'Unknown Resident').lower(), reverse=(direction == 'desc'))
            elif sort == 'timestamp':
                checked_in.sort(key=lambda x: x[5], reverse=(direction == 'desc'))

            logger.info(f"User {current_user.username} successfully loaded {len(checked_in)} checked-in residents")
            conn.commit()

    except Exception as e:
        logger.error(f"Error retrieving resident activity for user {current_user.username}: {str(e)}", exc_info=True)
        flash("Error loading resident activity.", "danger")
        log_audit_action(
            username=current_user.username,
            action='view_failed',
            target='resident_activity_tracker',
            details=f'Failed to load resident activity: {str(e)}'
        )

    return render_template('common/resident_activity_tracker.html', data=checked_in, sort=sort, direction=direction, 
                           locations=locations, buildings=buildings, view_type=view_type, selected_view=selected_view)

@resident_activity_tracker_bp.route('/live/check_out', methods=['POST'], strict_slashes=False)
@login_required
@limiter.limit("100/hour", key_func=user_key_func)
def check_out():
    mdoc = request.form.get('mdoc')
    location = request.form.get('location')
    local_tz = pytz.timezone(Config.TIMEZONE)
    current_timestamp = datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')

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
            log_audit_action(
                username=current_user.username,
                action='check_out',
                target=f'resident:{resident_name}',
                details=f'Checked out resident from {location}'
            )
            conn.commit()

            logger.info(f"User {current_user.username} successfully checked out resident {resident_name} from {location}")
            flash(f"Resident {resident_name} checked out successfully.", "success")

    except Exception as e:
        logger.error(f"Error during check out for resident {resident_name} by user {current_user.username}: {str(e)}", exc_info=True)
        flash(f"Failed to check out resident {resident_name}.", "danger")
        log_audit_action(
            username=current_user.username,
            action='check_out_failed',
            target=f'resident:{resident_name}',
            details=f'Failed to check out resident from {location}: {str(e)}'
        )

    return redirect(url_for('resident_activity_tracker.live_dashboard'))

@resident_activity_tracker_bp.route('/heatmap-data', methods=['GET'], strict_slashes=False)
@login_required
@limiter.limit("100/hour", key_func=user_key_func)
def heatmap_data():
    logger.debug(f"User {current_user.username} accessing heatmap data")
    
    date_filter = request.args.get('date_filter', '1 day')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            log_audit_action(
                username=current_user.username,
                action='view',
                target='heatmap',
                details=f'Accessed resident activity heatmap data with date_filter={date_filter}'
            )

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

            df = pd.DataFrame(data, columns=['mdoc', 'latest_time', 'name', 'unit', 'housing_unit', 'level', 'location'])
            df['timestamp'] = pd.to_datetime(df['latest_time'])
            df['time_bucket'] = df['timestamp'].dt.floor('H').dt.strftime('%Y-%m-%d %H:00')

            heatmap_data = df.groupby(['location', 'time_bucket']).size().unstack(fill_value=0)
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
        log_audit_action(
            username=current_user.username,
            action='view_failed',
            target='heatmap',
            details=f'Failed to load heatmap data: {str(e)}'
        )
        return jsonify({'error': 'Failed to generate heatmap data'}), 500

@resident_activity_tracker_bp.route('/heatmap', methods=['GET'], strict_slashes=False)
@login_required
def heatmap():
    logger.debug(f"User {current_user.username} accessing heatmap page")
    try:
        with get_db() as conn:
            c = conn.cursor()
            log_audit_action(
                username=current_user.username,
                action='view',
                target='heatmap_page',
                details='Accessed resident activity heatmap page'
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log for heatmap page access: {str(e)}")
    return render_template('common/heatmap.html')