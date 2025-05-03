from flask import Blueprint, render_template, abort, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.audit_logging import log_audit_action
from rezscan_app.utils.file_utils import allowed_file
from rezscan_app.utils.constants import IMPORT_HISTORY_TABLE_HEADERS
import csv
import io
import logging
from datetime import datetime
from rezscan_app.config import Config
import pytz
import sqlite3

logger = logging.getLogger(__name__)
import_history_bp = Blueprint('import_history', __name__)

@import_history_bp.route('/admin/residents/import/history', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
def view_import_history():
    username = current_user.username
    logger.debug(f"User {username} accessing import history")
    
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute('''
                SELECT id, timestamp, username, added, updated, deleted, failed, total
                FROM import_history
                ORDER BY timestamp DESC
            ''')
            history = c.fetchall()
            logger.info(f"User {username} viewed import history with {len(history)} records")
            log_audit_action(username, 'view', 'import_history', f"Viewed {len(history)} import records")
    except sqlite3.Error as e:
        logger.error(f"User {username} failed to fetch import history: {str(e)}")
        log_audit_action(username, 'error', 'import_history', f"Database error: {str(e)}")
        flash("Database error fetching import history.", "danger")
        history = []

    return render_template('residents/resident_import_history.html', history=history, IMPORT_HISTORY_TABLE_HEADERS=IMPORT_HISTORY_TABLE_HEADERS)

@import_history_bp.route('/admin/residents/import/history/<int:id>/view', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
def view_import_snapshot(id):
    username = current_user.username
    logger.debug(f"User {username} viewing import snapshot ID {id}")
    
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute("SELECT csv_content, timestamp, username FROM import_history WHERE id = ?", (id,))
            row = c.fetchone()
            if not row:
                logger.warning(f"User {username} attempted to view non-existent import ID {id}")
                log_audit_action(username, 'view_snapshot_failed', 'import_history', f"Import ID {id} not found")
                abort(404, "Import record not found")

            csv_content = row['csv_content']
            if not allowed_file('dummy.csv'):
                logger.warning(f"User {username} encountered invalid CSV for import ID {id}")
                log_audit_action(username, 'view_snapshot_failed', 'import_history', f"Invalid CSV for ID {id}")
                abort(400, "Invalid CSV content")

            stream = io.StringIO(csv_content)
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            rows = list(reader)

            logger.info(f"User {username} viewed import snapshot ID {id}")
            log_audit_action(username, 'view_snapshot', 'import_history', f"Viewed snapshot for import ID {id}")
            return render_template('residents/import_snapshot.html', headers=headers, rows=rows, 
                                  timestamp=row['timestamp'], user=row['username'], 
                                  IMPORT_HISTORY_TABLE_HEADERS=IMPORT_HISTORY_TABLE_HEADERS)

    except Exception as e:
        logger.error(f"User {username} failed to view snapshot ID {id}: {str(e)}")
        log_audit_action(username, 'error', 'import_history', f"Error viewing snapshot ID {id}: {str(e)}")
        flash(f"Error reading CSV content: {str(e)}", "danger")
        return redirect(url_for('import_history.view_import_history'))

@import_history_bp.route('/admin/residents/import/history/<int:id>/rollback', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def rollback_import(id):
    username = current_user.username
    logger.debug(f"User {username} initiating rollback for import ID {id}")
    
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute("SELECT * FROM resident_backups WHERE import_id = ?", (id,))
            backups = c.fetchall()
            if not backups:
                logger.warning(f"User {username} found no backups for import ID {id}")
                log_audit_action(username, 'rollback_failed', 'import_history', f"No backups for import ID {id}")
                flash("No backups found for this import.", "danger")
                return redirect(url_for('import_history.view_import_history'))

            c.execute("SELECT csv_content FROM import_history WHERE id = ?", (id,))
            row = c.fetchone()
            if not row:
                logger.warning(f"User {username} found no import record for ID {id}")
                log_audit_action(username, 'rollback_failed', 'import_history', f"Import ID {id} not found")
                flash("Import record not found.", "danger")
                return redirect(url_for('import_history.view_import_history'))

            csv_content = row['csv_content']
            if not allowed_file('dummy.csv'):
                logger.warning(f"User {username} encountered invalid CSV for import ID {id}")
                log_audit_action(username, 'rollback_failed', 'import_history', f"Invalid CSV for ID {id}")
                flash("Invalid CSV content.", "danger")
                return redirect(url_for('import_history.view_import_history'))

            stream = io.StringIO(csv_content)
            reader = csv.DictReader(stream)

            added = 0
            updated = 0
            deleted = 0
            failed = 0

            backup_mdocs = {row['mdoc'] for row in backups}
            for row in reader:
                mdoc = row.get('mdoc')
                if mdoc and mdoc not in backup_mdocs:
                    c.execute("DELETE FROM residents WHERE mdoc = ?", (mdoc,))
                    deleted += 1

            for b in backups:
                c.execute("SELECT * FROM residents WHERE mdoc = ?", (b['mdoc'],))
                exists = c.fetchone()
                if exists:
                    c.execute("UPDATE residents SET name=?, unit=?, housing_unit=?, level=?, photo=? WHERE mdoc = ?",
                              (b['name'], b['unit'], b['housing_unit'], b['level'], b['photo'], b['mdoc']))
                    updated += 1
                else:
                    c.execute("INSERT INTO residents (mdoc, name, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                              (b['mdoc'], b['name'], b['unit'], b['housing_unit'], b['level'], b['photo']))
                    added += 1

            db.commit()

            timestamp = datetime.now(pytz.timezone(Config.TIMEZONE)).isoformat()
            c.execute("""
                INSERT INTO import_history (timestamp, username, added, updated, deleted, failed, total, csv_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, username, added, updated, deleted, failed, added + updated + deleted, f'-- ROLLBACK OF IMPORT ID {id} --'))
            db.commit()

            logger.info(f"User {username} completed rollback for import ID {id}")
            log_audit_action(username, 'rollback_import', 'import_history', f"Rolled back import ID {id}: added={added}, updated={updated}, deleted={deleted}")
            flash(f"Rollback completed for import ID {id}.", "success")

    except Exception as e:
        db.rollback()
        logger.error(f"User {username} failed to rollback import ID {id}: {str(e)}")
        log_audit_action(username, 'rollback_failed', 'import_history', f"Rollback failed for ID {id}: {str(e)}")
        flash(f"Rollback failed: {str(e)}", "danger")

    return redirect(url_for('import_history.view_import_history'))