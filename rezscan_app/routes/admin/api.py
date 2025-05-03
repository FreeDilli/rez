from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.audit_logging import log_audit_action
from rezscan_app.config import Config
import logging
from datetime import datetime
import pytz
import sqlite3

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

# Initialize Limiter (configure in app.py and pass to blueprints)
limiter = Limiter(
    key_func=get_remote_address,  # Use IP for unauthenticated, override for authenticated
    default_limits=["200 per day", "50 per hour"]
)

# Override key_func for authenticated users
def user_key_func():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

@api_bp.route('/admin/api/status/<mdoc>', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
@limiter.limit("100/hour", key_func=user_key_func)
def get_resident_status(mdoc):
    username = current_user.username
    logger.debug(f"User {username} checking status for MDOC {mdoc}")
    
    try:
        db = get_db()
        c = db.cursor()

        c.execute("SELECT id, name FROM residents WHERE mdoc = ?", (mdoc,))
        resident = c.fetchone()
        if not resident:
            logger.warning(f"User {username} queried non-existent MDOC {mdoc}")
            log_audit_action(username, 'view_status_failed', 'resident', f"MDOC {mdoc} not found")
            return jsonify({
                "mdoc": mdoc,
                "status": "Not Found",
                "message": f"Resident with MDOC {mdoc} not found."
            }), 404

        resident_id, name = resident

        c.execute("SELECT timestamp, status, location FROM scans WHERE mdoc = ? ORDER BY timestamp DESC LIMIT 1", (mdoc,))
        scan = c.fetchone()

        if not scan:
            logger.info(f"User {username} found no scans for MDOC {mdoc}")
            log_audit_action(username, 'view_status', 'resident', f"No scans for MDOC {mdoc}")
            return jsonify({
                "mdoc": mdoc,
                "name": name,
                "status": "No Scans Found"
            })

        timestamp, status, location = scan
        local_tz = pytz.timezone(Config.TIMEZONE)
        utc_dt = datetime.fromisoformat(timestamp.replace('T', ' '))
        local_dt = utc_dt.astimezone(local_tz)
        local_timestamp = local_dt.strftime('%Y-%m-%d %H:%M:%S')

        log_audit_action(username, 'view_status', 'resident', f"Checked status for MDOC {mdoc}")
        logger.info(f"User {username} retrieved status for MDOC {mdoc}")
        return jsonify({
            "mdoc": mdoc,
            "name": name,
            "last_location": location,
            "last_status": status,
            "timestamp": local_timestamp,
            "status": "Scanned In" if status == 'in' else "Scanned Out"
        })

    except sqlite3.Error as e:
        logger.error(f"User {username} encountered database error checking MDOC {mdoc}: {str(e)}")
        log_audit_action(username, 'error', 'resident', f"Database error for MDOC {mdoc}: {str(e)}")
        return jsonify({"status": "error", "message": "Database error."}), 500

@api_bp.route('/admin/api/scan', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
@limiter.limit("50/hour", key_func=user_key_func)
def api_scan():
    username = current_user.username
    logger.debug(f"User {username} recording scan via API")
    
    try:
        db = get_db()
        c = db.cursor()

        data = request.get_json()
        mdoc = data.get('mdoc')
        location = data.get('location')
        direction = data.get('direction')

        if not all([mdoc, location, direction]):
            logger.warning(f"User {username} provided incomplete scan data: {data}")
            log_audit_action(username, 'scan_failed', 'scan', "Missing required fields")
            return jsonify({
                "status": "error",
                "message": "Missing required fields: mdoc, location, direction."
            }), 400

        c.execute("SELECT name FROM residents WHERE mdoc = ?", (mdoc,))
        resident = c.fetchone()

        if not resident:
            logger.warning(f"User {username} attempted scan for non-existent MDOC {mdoc}")
            log_audit_action(username, 'scan_failed', 'scan', f"MDOC {mdoc} not found")
            return jsonify({
                "status": "error",
                "message": f"Resident with MDOC {mdoc} not found."
            }), 404

        name = resident[0]
        now = datetime.now(pytz.timezone(Config.TIMEZONE))
        timestamp = now.isoformat()

        c.execute('''
            INSERT INTO scans (mdoc, timestamp, status, location)
            VALUES (?, ?, ?, ?)
        ''', (mdoc, timestamp, direction, location))
        db.commit()

        log_audit_action(username, 'scan', 'scan', f"Recorded scan for MDOC {mdoc} at {location}")
        logger.info(f"User {username} recorded scan for MDOC {mdoc} at {location}")
        return jsonify({
            "status": "success",
            "message": f"Scan recorded: {name} - {direction.upper()} at {location}.",
            "timestamp": timestamp
        }), 201

    except sqlite3.Error as e:
        logger.error(f"User {username} encountered database error recording scan: {str(e)}")
        log_audit_action(username, 'scan_failed', 'scan', f"Database error: {str(e)}")
        return jsonify({"status": "error", "message": "Database error."}), 500