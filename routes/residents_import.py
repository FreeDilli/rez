from flask import Blueprint, render_template, request, jsonify, g
from utils.logging_config import setup_logging
from models.database import get_db
import csv
import io
import logging
from datetime import datetime
from routes.auth import login_required, role_required
from utils.file_utils import allowed_file
from utils.constants import CSV_REQUIRED_HEADERS, CSV_OPTIONAL_HEADERS

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

residents_import_bp = Blueprint('residents_import', __name__)

@residents_import_bp.route('/admin/residents/import', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
def import_residents():
    return render_template('import_residents.html', 
                          CSV_REQUIRED_HEADERS=CSV_REQUIRED_HEADERS, 
                          CSV_OPTIONAL_HEADERS=CSV_OPTIONAL_HEADERS)

@residents_import_bp.route('/admin/residents/import/upload', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def upload_residents():
    messages = []
    stats = {
        'added': 0,
        'updated': 0,
        'deleted': 0,
        'failed': 0,
        'processed': 0
    }
    preview_changes = []
    update_diffs = []
    backup_entries = []

    file = request.files.get('csv_file')
    dry_run = request.form.get('dry_run') == 'yes'

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'}), 400
    elif not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Only CSV files allowed.'}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        reader = csv.DictReader(stream)
        reader.fieldnames = [f.lower() for f in reader.fieldnames]

        csv_data = {}
        for raw_row in reader:
            row = {k.lower(): v for k, v in raw_row.items()}

            if not row.get('mdoc'):
                stats['failed'] += 1
                messages.append(f"✘ Missing MDOC for row: {raw_row}")
                continue

            # Replace multiple phrases in housing_unit
            housing_unit = row.get('housing_unit', '')
            replacements = {
                'women ctr': "Women's Center",
                'swmrc': "smwrc"
            }
            if housing_unit in replacements:
                row['housing_unit'] = replacements[housing_unit]

            csv_data[row['mdoc']] = row

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM residents")
        existing = {row['mdoc']: dict(row) for row in c.fetchall()}

        for mdoc, new_data in csv_data.items():
            stats['processed'] += 1
            if mdoc not in existing:
                preview_changes.append(f"➕ Add: {new_data['name']}")
                stats['added'] += 1
                if not dry_run:
                    try:
                        c.execute("INSERT INTO residents (name, mdoc, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                                  (new_data['name'], new_data['mdoc'], new_data['unit'], new_data.get('housing_unit', ''), new_data['level'], new_data.get('photo', '')))
                    except Exception as e:
                        stats['failed'] += 1
                        messages.append(f"✘ Error adding {new_data['name']}: {str(e)}")
            else:
                current = existing[mdoc]
                diffs = {}
                for field in ['name', 'unit', 'housing_unit', 'level', 'photo']:
                    if str(current[field]) != str(new_data.get(field, '')):
                        diffs[field] = {'from': current[field], 'to': new_data.get(field, '')}

                if diffs:
                    preview_changes.append(f"✏️ Update: {new_data['name']}")
                    update_diffs.append({
                        'mdoc': mdoc,
                        'name': new_data['name'],
                        'diffs': diffs
                    })
                    stats['updated'] += 1
                    if not dry_run:
                        try:
                            backup_entries.append((mdoc, current['name'], current['unit'], current['housing_unit'], current['level'], current['photo']))
                            c.execute("UPDATE residents SET name=?, unit=?, housing_unit=?, level=?, photo=? WHERE mdoc=?",
                                      (new_data['name'], new_data['unit'], new_data.get('housing_unit', ''), new_data['level'], new_data.get('photo', ''), mdoc))
                        except Exception as e:
                            stats['failed'] += 1
                            messages.append(f"✘ Error updating {new_data['name']}: {str(e)}")

        for mdoc in existing:
            if mdoc not in csv_data:
                preview_changes.append(f"❌ Delete: {existing[mdoc]['name']}")
                stats['deleted'] += 1
                if not dry_run:
                    try:
                        current = existing[mdoc]
                        backup_entries.append((mdoc, current['name'], current['unit'], current['housing_unit'], current['level'], current['photo']))
                        c.execute("DELETE FROM residents WHERE mdoc = ?", (mdoc,))
                    except Exception as e:
                        stats['failed'] += 1
                        messages.append(f"✘ Error deleting MDOC {mdoc}: {str(e)}")

        if not dry_run:
            db.commit()
            messages.append("✅ Changes committed to database.")

            # Log import to history
            try:
                user = g.user['username'] if 'user' in g else 'unknown'
                timestamp = datetime.utcnow().isoformat()
                summary = (stats['added'], stats['updated'], stats['deleted'], stats['failed'], stats['processed'])

                file.stream.seek(0)
                raw_csv = file.stream.read().decode("utf-8-sig")

                c.execute("""
                    INSERT INTO import_history (timestamp, username, added, updated, deleted, failed, total, csv_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, user, *summary, raw_csv))
                import_id = c.lastrowid

                for b in backup_entries:
                    c.execute("""
                        INSERT INTO resident_backups (import_id, mdoc, name, unit, housing_unit, level, photo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (import_id, *b))

                db.commit()
                logger.info(f"Logged import to history: {user} @ {timestamp} with {len(backup_entries)} backup(s)")
            except Exception as e:
                logger.warning(f"Failed to log import history or backups: {e}")
        else:
            messages.append("🧪 Dry Run: No changes committed.")

        return jsonify({
            'success': True,
            'messages': messages,
            'stats': stats,
            'preview_changes': preview_changes,
            'update_diffs': update_diffs
        })

    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}")
        return jsonify({'success': False, 'message': f"Error reading CSV: {str(e)}"}), 500