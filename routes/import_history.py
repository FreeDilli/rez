from flask import Blueprint, render_template, abort, redirect, url_for, flash, g
from models.database import get_db
from routes.auth import login_required, role_required
import csv
import io
from datetime import datetime
from utils.file_utils import allowed_file
from utils.constants import IMPORT_HISTORY_TABLE_HEADERS  # Import constant

import_history_bp = Blueprint('import_history', __name__)

@import_history_bp.route('/admin/residents/import/history', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
def view_import_history():
    with get_db() as db:
        c = db.cursor()
        c.execute('''
            SELECT id, timestamp, username, added, updated, deleted, failed, total
            FROM import_history
            ORDER BY timestamp DESC
        ''')
        history = c.fetchall()
    return render_template('import_history.html', history=history, IMPORT_HISTORY_TABLE_HEADERS=IMPORT_HISTORY_TABLE_HEADERS)

@import_history_bp.route('/admin/residents/import/history/<int:id>/view', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
def view_import_snapshot(id):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT csv_content, timestamp, username FROM import_history WHERE id = ?", (id,))
        row = c.fetchone()
        if not row:
            abort(404, "Import record not found")

        csv_content = row['csv_content']
        if not allowed_file('dummy.csv'):
            abort(400, "Invalid CSV content")
        try:
            stream = io.StringIO(csv_content)
            reader = csv.DictReader(stream)
            headers = reader.fieldnames
            rows = list(reader)
        except Exception as e:
            flash(f"Error reading CSV content: {str(e)}", "danger")
            return redirect(url_for('import_history.view_import_history'))

        return render_template('import_snapshot.html', headers=headers, rows=rows, 
                              timestamp=row['timestamp'], user=row['username'], 
                              IMPORT_HISTORY_TABLE_HEADERS=IMPORT_HISTORY_TABLE_HEADERS)

@import_history_bp.route('/admin/residents/import/history/<int:id>/rollback', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def rollback_import(id):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT * FROM resident_backups WHERE import_id = ?", (id,))
        backups = c.fetchall()
        if not backups:
            flash("No backups found for this import.", "danger")
            return redirect(url_for('import_history.view_import_history'))

        try:
            backup_mdocs = {row['mdoc'] for row in backups}
            c.execute("SELECT csv_content FROM import_history WHERE id = ?", (id,))
            row = c.fetchone()
            if not row:
                flash("Import record not found.", "danger")
                return redirect(url_for('import_history.view_import_history'))

            csv_content = row['csv_content']
            if not allowed_file('dummy.csv'):
                flash("Invalid CSV content.", "danger")
                return redirect(url_for('import_history.view_import_history'))

            stream = io.StringIO(csv_content)
            reader = csv.DictReader(stream)

            added = 0
            updated = 0
            deleted = 0
            failed = 0

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

            timestamp = datetime.utcnow().isoformat()
            user = g.user['username'] if 'user' in g else 'unknown'
            c.execute("""
                INSERT INTO import_history (timestamp, username, added, updated, deleted, failed, total, csv_content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, user, added, updated, deleted, failed, added + updated + deleted, f'-- ROLLBACK OF IMPORT ID {id} --'))
            db.commit()

            flash(f"Rollback completed for import ID {id}.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Rollback failed: {str(e)}", "danger")

        return redirect(url_for('import_history.view_import_history'))