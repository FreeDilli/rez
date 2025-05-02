from flask import Blueprint, render_template, request, send_file, flash, url_for, redirect
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
import io
import csv
import logging
from datetime import datetime
import pytz
import re
import sqlite3

audit_log_bp = Blueprint('audit_log', __name__)
logger = logging.getLogger(__name__)
def log_audit_action(username, action, target, details=None):
    """Helper function to log actions to audit_log table and logger."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)",
                (username, action, target, details)
            )
            conn.commit()
            logger.debug(f"Audit log created: {username} - {action} - {target}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for {username}: {str(e)}")

# Pagination settings
PER_PAGE = 10

def parse_and_convert_timestamp(text, local_tz):
    """Convert UTC timestamps in text (e.g., in details) to local time."""
    # Match ISO timestamps like 2025-04-28T00:01:43.692232
    iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?'
    matches = re.findall(iso_pattern, text)
    for match in matches:
        try:
            utc_dt = datetime.fromisoformat(match.replace('T', ' '))
            utc_dt = pytz.utc.localize(utc_dt)
            local_dt = utc_dt.astimezone(local_tz)
            local_str = local_dt.strftime('%m-%d-%Y %H:%M:%S')
            text = text.replace(match, local_str)
        except ValueError:
            continue
    return text

@audit_log_bp.route('/admin/auditlog', methods=['GET'])
@login_required
def view_audit_log():
    logger.debug(f"User {current_user.username} accessing audit log")

    username = current_user.username if current_user.is_authenticated else 'unknown'
    log_audit_action(
        username=username,
        action='view',
        target='audit_log',
        details='Viewed audit log page'
    )

    username_filter = request.args.get('username', '').strip()
    action_filter = request.args.get('action', '').strip()
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    page = int(request.args.get('page', 1))

    query = "SELECT id, timestamp, username, action, target, details FROM audit_log WHERE 1=1"
    params = []
    local_tz = pytz.timezone('America/New_York')  # Change to your timezone

    if username_filter:
        query += " AND username LIKE ?"
        params.append(f"%{username_filter}%")
    if action_filter:
        query += " AND action = ?"
        params.append(action_filter)
    if start_date:
        try:
            local_dt = datetime.strptime(start_date, '%Y-%m-%d')
            local_dt = local_tz.localize(local_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
            query += " AND DATE(timestamp) >= ?"
            params.append(utc_dt.strftime('%Y-%m-%d'))
        except ValueError:
            flash("Invalid start date format.", "warning")
    if end_date:
        try:
            local_dt = datetime.strptime(end_date, '%Y-%m-%d')
            local_dt = local_tz.localize(local_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
            query += " AND DATE(timestamp) <= ?"
            params.append(utc_dt.strftime('%Y-%m-%d'))
        except ValueError:
            flash("Invalid end date format.", "warning")

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([PER_PAGE, (page - 1) * PER_PAGE])

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(query, params)
            rows = c.fetchall()

            # Convert timestamps to local time
            logs = []
            for row in rows:
                # Convert main timestamp
                utc_dt = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                utc_dt = pytz.utc.localize(utc_dt)
                local_dt = utc_dt.astimezone(local_tz)
                local_timestamp = local_dt.strftime('%Y-%m-%d %H:%M:%S')  # For filters
                # Convert timestamps in details
                details = parse_and_convert_timestamp(row[5] or '', local_tz)
                logs.append((row[0], local_timestamp, row[2], row[3], row[4], details))

            # Get total count
            c.execute("SELECT COUNT(*) FROM audit_log WHERE 1=1" + _build_filter_clause(username_filter, action_filter, start_date, end_date, local_tz), _build_filter_params(username_filter, action_filter, start_date, end_date, local_tz))
            total_logs = c.fetchone()[0]

            # Fetch distinct actions
            c.execute("SELECT DISTINCT action FROM audit_log ORDER BY action")
            actions = [row[0] for row in c.fetchall()]

            total_pages = max((total_logs + PER_PAGE - 1) // PER_PAGE, 1)

    except Exception as e:
        logger.error(f"Error fetching audit log: {e}")
        flash("Error loading audit logs.", "danger")
        logs = []
        total_pages = 1
        actions = []

    return render_template('audit_log.html',
                           logs=logs,
                           page=page,
                           total_pages=total_pages,
                           username_filter=username_filter,
                           action_filter=action_filter,
                           start_date=start_date,
                           end_date=end_date,
                           actions=actions)

def _build_filter_clause(username, action, start_date, end_date, local_tz):
    clause = ""
    if username:
        clause += " AND username LIKE ?"
    if action:
        clause += " AND action = ?"
    if start_date:
        clause += " AND DATE(timestamp) >= ?"
    if end_date:
        clause += " AND DATE(timestamp) <= ?"
    return clause

def _build_filter_params(username, action, start_date, end_date, local_tz):
    params = []
    if username:
        params.append(f"%{username}%")
    if action:
        params.append(action)
    if start_date:
        try:
            local_dt = datetime.strptime(start_date, '%Y-%m-%d')
            local_dt = local_tz.localize(local_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
            params.append(utc_dt.strftime('%Y-%m-%d'))
        except ValueError:
            pass
    if end_date:
        try:
            local_dt = datetime.strptime(end_date, '%Y-%m-%d')
            local_dt = local_tz.localize(local_dt)
            utc_dt = local_dt.astimezone(pytz.utc)
            params.append(utc_dt.strftime('%Y-%m-%d'))
        except ValueError:
            pass
    return params

@audit_log_bp.route('/export', methods=['GET'])
@login_required
def export_audit_log():
    logger.debug(f"User {current_user.username} requested audit log export")

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT timestamp, username, action, target, details FROM audit_log ORDER BY timestamp DESC")
            rows = c.fetchall()

            # Convert timestamps to local time
            local_tz = pytz.timezone('America/New_York')  # Change to your timezone
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Timestamp", "Username", "Action", "Target", "Details"])

            for row in rows:
                utc_dt = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                utc_dt = pytz.utc.localize(utc_dt)
                local_dt = utc_dt.astimezone(local_tz)
                local_timestamp = local_dt.strftime('%m-%d-%Y %H:%M:%S')  # For CSV
                details = parse_and_convert_timestamp(row[4] or '', local_tz)
                writer.writerow([local_timestamp, row[1], row[2], row[3], details])

            output.seek(0)
            return send_file(io.BytesIO(output.getvalue().encode()),
                             mimetype='text/csv',
                             as_attachment=True,
                             download_name='audit_log_export.csv')

    except Exception as e:
        logger.error(f"Failed to export audit log: {e}")
        flash("Error exporting audit log.", "danger")
        return redirect(url_for('audit_log.view_audit_log'))