# rezscan_app/routes/audit_log.py
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from rezscan_app.routes.auth import role_required
from rezscan_app.models.database import get_db
import logging

audit_log_bp = Blueprint('audit_log', __name__, url_prefix='/admin/auditlog')
logger = logging.getLogger(__name__)

@audit_log_bp.route('/', methods=['GET'])
@login_required
@role_required('admin')
def view_audit_log():
    username_filter = request.args.get('username', '').strip()
    action_filter = request.args.get('action', '').strip()

    try:
        with get_db() as conn:
            c = conn.cursor()

            query = '''
                SELECT username, action, target, details, timestamp
                FROM audit_log
                WHERE 1=1
            '''
            params = []

            if username_filter:
                query += ' AND username LIKE ?'
                params.append(f'%{username_filter}%')

            if action_filter:
                query += ' AND action LIKE ?'
                params.append(f'%{action_filter}%')

            query += ' ORDER BY timestamp DESC LIMIT 500'

            c.execute(query, params)
            logs = c.fetchall()

    except Exception as e:
        logger.error(f"Error retrieving audit logs: {e}")
        logs = []

    return render_template('audit_log.html', logs=logs, username_filter=username_filter, action_filter=action_filter)
