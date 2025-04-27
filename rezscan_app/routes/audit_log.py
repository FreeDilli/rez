from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import role_required
import csv
import io
import logging
from datetime import datetime

audit_log_bp = Blueprint('audit_log', __name__, url_prefix='/auditlog')
logger = logging.getLogger(__name__)

@audit_log_bp.route('/', methods=['GET'])
@login_required
@role_required('admin')
def view_audit_log():
    try:
        username = request.args.get('username', '')
        action = request.args.get('action', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))

        query = '''
            SELECT id, timestamp, username, action, target, details
            FROM audit_log
            WHERE 1=1
        '''
        params = []

        if username:
            query += " AND username LIKE ?"
            params.append(f"%{username}%")
        if action:
            query += " AND action LIKE ?"
            params.append(f"%{action}%")
        if start_date:
            query += " AND date(timestamp) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date(timestamp) <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params += [per_page, (page - 1) * per_page]

        with get_db() as conn:
            c = conn.cursor()
            c.execute(query, params)
            logs = c.fetchall()

            # Total count for pagination
            c.execute('SELECT COUNT(*) FROM audit_log')
            total_logs = c.fetchone()[0]

        total_pages = (total_logs + per_page - 1) // per_page

        return render_template(
            'audit_log.html',
            logs=logs,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error fetching audit log: {str(e)}")
        flash('Error loading audit log.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@audit_log_bp.route('/export', methods=['GET'])
@login_required
@role_required('admin')
def export_audit_log():
    try:
        username = request.args.get('username', '')
        action = request.args.get('action', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        full_export = request.args.get('full_export')

        query = '''
            SELECT timestamp, username, action, target, details
            FROM audit_log
            WHERE 1=1
        '''
        params = []

        if not full_export:
            if username:
                query += " AND username LIKE ?"
                params.append(f"%{username}%")
            if action:
                query += " AND action LIKE ?"
                params.append(f"%{action}%")
            if start_date:
                query += " AND date(timestamp) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date(timestamp) <= ?"
                params.append(end_date)

        query += " ORDER BY timestamp DESC"

        with get_db() as conn:
            c = conn.cursor()
            c.execute(query, params)
            logs = c.fetchall()

        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Timestamp', 'Username', 'Action', 'Target', 'Details'])
        for row in logs:
            cw.writerow(row)

        output = si.getvalue().encode('utf-8')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"audit_log_export_{timestamp}.csv"

        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        logger.error(f"Error exporting audit log: {str(e)}")
        flash('Error exporting audit log.', 'danger')
        return redirect(url_for('audit_log.view_audit_log'))
