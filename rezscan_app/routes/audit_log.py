from flask import Blueprint, render_template, request, send_file, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
import io
import csv
import logging

audit_log_bp = Blueprint('audit_log', __name__, url_prefix='/auditlog')
logger = logging.getLogger(__name__)

# Pagination settings
PER_PAGE = 25

@audit_log_bp.route('/', methods=['GET'])
@login_required
def view_audit_log():
    logger.debug(f"User {current_user.username} accessing audit log")

    username_filter = request.args.get('username', '').strip()
    action_filter = request.args.get('action', '').strip()
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    page = int(request.args.get('page', 1))

    query = "SELECT id, timestamp, username, action, target, details FROM audit_log WHERE 1=1"
    params = []

    if username_filter:
        query += " AND username LIKE ?"
        params.append(f"%{username_filter}%")
    if action_filter:
        query += " AND action LIKE ?"
        params.append(f"%{action_filter}%")
    if start_date:
        query += " AND DATE(timestamp) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND DATE(timestamp) <= ?"
        params.append(end_date)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([PER_PAGE, (page - 1) * PER_PAGE])

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(query, params)
            logs = c.fetchall()

            # Get total count
            c.execute("SELECT COUNT(*) FROM audit_log WHERE 1=1" + _build_filter_clause(username_filter, action_filter, start_date, end_date), _build_filter_params(username_filter, action_filter, start_date, end_date))
            total_logs = c.fetchone()[0]

            total_pages = max((total_logs + PER_PAGE - 1) // PER_PAGE, 1)

    except Exception as e:
        logger.error(f"Error fetching audit log: {e}")
        flash("Error loading audit logs.", "danger")
        logs = []
        total_pages = 1

    return render_template('audit_log.html',
                           logs=logs,
                           page=page,
                           total_pages=total_pages,
                           username_filter=username_filter,
                           action_filter=action_filter,
                           start_date=start_date,
                           end_date=end_date)

def _build_filter_clause(username, action, start_date, end_date):
    clause = ""
    if username:
        clause += " AND username LIKE ?"
    if action:
        clause += " AND action LIKE ?"
    if start_date:
        clause += " AND DATE(timestamp) >= ?"
    if end_date:
        clause += " AND DATE(timestamp) <= ?"
    return clause

def _build_filter_params(username, action, start_date, end_date):
    params = []
    if username:
        params.append(f"%{username}%")
    if action:
        params.append(f"%{action}%")
    if start_date:
        params.append(start_date)
    if end_date:
        params.append(end_date)
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

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Username", "Action", "Target", "Details"])

        for row in rows:
            writer.writerow(row)

        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode()),
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='audit_log_export.csv')

    except Exception as e:
        logger.error(f"Failed to export audit log: {e}")
        flash("Error exporting audit log.", "danger")
        return redirect(url_for('audit_log.view_audit_log'))
