from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from rezscan_app.models.database import get_db
from flask_login import login_required, current_user
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.logging_config import setup_logging
from rezscan_app.utils.constants import LOCATION_TYPES
from rezscan_app.utils.audit_logging import log_audit_action
import sqlite3
import logging
from rezscan_app.config import Config
import pytz

setup_logging()
logger = logging.getLogger(__name__)

locations_bp = Blueprint('locations', __name__)

@locations_bp.route('/admin/locations', methods=['GET', 'POST'], strict_slashes=False)
@login_required
@role_required('admin')
def manage_locations():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/locations route, method: {request.method}")
    locations = []
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            if request.method == 'POST':
                bldg = request.form['bldg'].strip()
                name = request.form['name'].strip()
                prefix = request.form['prefix'].strip().upper()
                location_type = request.form['type'].strip()
                
                if not (bldg and name and prefix and location_type):
                    flash("All fields are required.", "warning")
                    log_audit_action(username, 'add_location_failed', 'locations', 'Missing required fields')
                    logger.warning(f"User {username} failed to add location: missing fields")
                elif not prefix.isalnum():
                    flash("Prefix must be alphanumeric.", "warning")
                    log_audit_action(username, 'add_location_failed', 'locations', 'Invalid prefix (non-alphanumeric)')
                    logger.warning(f"User {username} failed to add location: invalid prefix")
                else:
                    try:
                        c.execute("INSERT INTO locations (bldg, name, prefix, type) VALUES (?, ?, ?, ?)", (bldg, name, prefix, location_type))
                        conn.commit()
                        flash(f"Location '{name}' added.", "success")
                        log_audit_action(username, 'add_location', 'locations', f"Added location: {name}, bldg: {bldg}, prefix: {prefix}, type: {location_type}")
                        logger.info(f"User {username} added location: {name}")
                    except sqlite3.IntegrityError as e:
                        flash("Location or prefix already exists.", "warning")
                        log_audit_action(username, 'add_location_failed', 'locations', f"Integrity error: {str(e)}")
                        logger.error(f"User {username} failed to add location: {str(e)}")
            
            c.execute("SELECT id, bldg, name, prefix, type FROM locations ORDER BY name")
            locations = c.fetchall()
            logger.debug(f"User {username} fetched {len(locations)} locations")
            log_audit_action(username, 'view', 'locations', f"Viewed {len(locations)} locations")
            
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} in manage_locations: {str(e)}")
        log_audit_action(username, 'error', 'locations', f"Database error: {str(e)}")
        flash("Database error occurred.", "danger")
    
    return render_template('admin/scan_locations.html', locations=locations, LOCATION_TYPES=LOCATION_TYPES)

@locations_bp.route('/admin/locations/delete/<int:location_id>', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_location(location_id):
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/locations/delete/{location_id} route")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM locations WHERE id = ?", (location_id,))
            location_name = c.fetchone()
            location_name = location_name[0] if location_name else 'unknown'
            
            c.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            deleted_rows = c.rowcount
            conn.commit()
            
            if deleted_rows > 0:
                log_audit_action(username, 'delete_location', 'locations', f"Deleted location: {location_name} (ID: {location_id})")
                logger.info(f"User {username} deleted location: {location_name} (ID: {location_id})")
                flash("Location deleted successfully.", "success")
            else:
                log_audit_action(username, 'delete_location_failed', 'locations', f"Location ID {location_id} not found")
                logger.warning(f"User {username} failed to delete location ID {location_id}: not found")
                flash("Location not found.", "warning")
                
    except sqlite3.Error as e:
        logger.error(f"Error deleting location ID {location_id} for user {username}: {str(e)}")
        log_audit_action(username, 'delete_location_failed', 'locations', f"Database error: {str(e)}")
        flash("Error deleting location.", "danger")
    
    return redirect(url_for('locations.manage_locations'))