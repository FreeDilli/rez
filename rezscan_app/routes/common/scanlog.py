from flask import Blueprint, render_template, redirect, url_for, flash, send_file, request
from flask_login import current_user, login_required
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.logging_config import setup_logging
from rezscan_app.utils.constants import DATEFORMAT, TIMEFORMAT
import logging
import sqlite3
import io
import csv
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rezscan_app.utils.audit_logging import log_audit_action

setup_logging()
logger = logging.getLogger(__name__)

scanlog_bp = Blueprint('scanlog', __name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def user_key_func():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

@scanlog_bp.route('/scanlog', methods=['GET'], strict_slashes=False)
@login_required
def scanlog():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/scanlog route")
    
    # Pagination and filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    location = request.args.get('location', '')
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            
            # Build query with filters
            query = 'SELECT * FROM scans_with_residents WHERE 1=1'
            count_query = 'SELECT COUNT(*) FROM scans_with_residents WHERE 1=1'
            params = []
            
            if search:
                query += ' AND (mdoc LIKE ? OR name LIKE ?)'
                count_query += ' AND (mdoc LIKE ? OR name LIKE ?)'
                search_param = f'%{search}%'
                params.extend([search_param, search_param])
            
            if status:
                query += ' AND status = ?'
                count_query += ' AND status = ?'
                params.append(status)
            
            if location:
                query += ' AND location = ?'
                count_query += ' AND location = ?'
                params.append(location)
            
            # Get total count
            c.execute(count_query, params)
            total_records = c.fetchone()[0]
            total_pages = (total_records + per_page - 1) // per_page
            
            # Fetch paginated data
            query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
            params.extend([per_page, offset])
            c.execute(query, params)
            data = c.fetchall()
            logger.debug(f"User {username} fetched {len(data)} scan records for page {page}")
            
            c.execute('SELECT DISTINCT status FROM scans_with_residents ORDER BY status')
            status_options = [row[0] for row in c.fetchall() if row[0]]
            
            c.execute('SELECT DISTINCT location FROM scans_with_residents ORDER BY location')
            location_options = [row[0] for row in c.fetchall() if row[0]]
            
            log_audit_action(
                username=username,
                action='view',
                target='scanlog',
                details=f"Viewed scanlog page {page} with {len(data)} records, search='{search}', status='{status}', location='{location}'"
            )
            
            logger.info(f"User {username} successfully retrieved scanlog data for page {page}")
            return render_template(
                'common/scanlog.html', 
                scans=data, 
                status_options=status_options, 
                location_options=location_options,
                page=page,
                total_pages=total_pages,
                per_page=per_page,
                total_records=total_records,
                search=search,
                status=status,
                location=location
            )
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} in scanlog: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog',
            details=f"Database error: {str(e)}"
        )
        return render_template('common/error.html', message=f"Database error: {str(e)}"), 500
    
@scanlog_bp.route('/scanlog/delete', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
@limiter.limit("10/day", key_func=user_key_func)
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
            return redirect(url_for('admin.admin_dashboard'))
    except sqlite3.Error as e:
        logger.error(f"Error deleting scan logs for user {username}: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog_delete',
            details=f"Error deleting scan logs: {str(e)}"
        )
        flash("Error deleting scan logs.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

@scanlog_bp.route('/scanlog/export', strict_slashes=False)
@login_required
@role_required('admin')
@limiter.limit("50/hour", key_func=user_key_func)
def export_scanlog():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/scanlog/export route")
    
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['MDOC', 'Name', 'Date', 'Time', 'Status', 'Location'])
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT mdoc, name, timestamp, status, location FROM scans_with_residents ORDER BY timestamp DESC")
            rows = c.fetchall()
            
            for row in rows:
                timestamp = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S') if row[2] else None
                date_str = timestamp.strftime(DATEFORMAT) if timestamp else ''
                time_str = timestamp.strftime(TIMEFORMAT) if timestamp else ''
                writer.writerow([row[0], row[1], date_str, time_str, row[3], row[4]])
            
            logger.info(f"User {username} exported {len(rows)} scanlog records to CSV")
            log_audit_action(
                username=username,
                action='export',
                target='scanlog',
                details=f"Exported {len(rows)} scanlog records to CSV"
            )
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='scanlog.csv'
        )
    
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} during scanlog export: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog_export',
            details=f"Database error during export: {str(e)}"
        )
        flash("Error exporting scanlog.", "danger")
        return redirect(url_for('scanlog.scanlog'))
    except ValueError as e:
        logger.error(f"Timestamp parsing error for user {username} during scanlog export: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog_export',
            details=f"Timestamp parsing error: {str(e)}"
        )
        flash("Error exporting scanlog due to invalid timestamp format.", "danger")
        return redirect(url_for('scanlog.scanlog'))
    except Exception as e:
        logger.error(f"Unexpected error for user {username} during scanlog export: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='scanlog_export',
            details=f"Unexpected error during export: {str(e)}"
        )
        flash("Error exporting scanlog.", "danger")
        return redirect(url_for('scanlog.scanlog'))