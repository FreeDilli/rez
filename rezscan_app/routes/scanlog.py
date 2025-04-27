from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required, role_required
from rezscan_app.utils.logging_config import setup_logging
import logging
import sqlite3

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

scanlog_bp = Blueprint('scanlog', __name__)

def log_audit_action(username, action, target, details=None):
    """Insert an audit log entry into the audit_log table."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)',
                (username, action, target, details)
            )
            conn.commit()
            logger.debug(f"Audit log created: {username} - {action} - {target}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for {username}: {str(e)}")

@scanlog_bp.route('/admin/scanlog', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def scanlog():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/scanlog route")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM scans_with_residents ORDER BY timestamp DESC')
            data = c.fetchall()
            logger.debug(f"User {username} fetched {len(data)} scan records")
            
            c.execute('SELECT DISTINCT status FROM scans_with_residents ORDER BY status')
            status_options = [row[0] for row in c.fetchall() if row[0]]
            logger.debug(f"User {username} fetched {len(status_options)} status options")
            
            c.execute('SELECT DISTINCT location FROM scans_with_residents ORDER BY location')
            location_options = [row[0] for row in c.fetchall() if row[0]]
            logger.debug(f"User {username} fetched {len(location_options)} location options")
            
            log_audit_action(
                username=username,
                action='view',
                target='scanlog',
                details=f"Viewed scanlog with {len(data)} records"
            )
            
            logger.info(f"User {username} successfully retrieved scanlog data")
            return render_template('scanlog.html', scans=data, status_options=status_options, location_options=location_options)
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} in scanlog: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog',
            details=f"Database error: {str(e)}"
        )
        return render_template('error.html', message=f"Database error: {str(e)}"), 500
    
@scanlog_bp.route('/admin/scanlog/delete', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_scanlog():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/scanlog/delete route")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM scans")
            deleted_rows = c.rowcount
            conn.commit()
            
            log_audit_action(
                username=username,
                action='delete',
                target='scanlog',
                details=f"Deleted {deleted_rows} scan records"
            )
            
            logger.info(f"User {username} deleted {deleted_rows} scan logs")
            flash("All scan logs deleted successfully.", "success")
            return redirect(url_for('scanlog.scanlog'))
    except sqlite3.Error as e:
        logger.error(f"Error deleting scan logs for user {username}: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog_delete',
            details=f"Error deleting scan logs: {str(e)}"
        )
        flash("Error deleting scan logs.", "error")
        return redirect(url_for('scanlog.scanlog'))