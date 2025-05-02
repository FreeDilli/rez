from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, g
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from rezscan_app.routes.common.auth import role_required
from rezscan_app.utils.constants import UNIT_OPTIONS, HOUSING_OPTIONS, LEVEL_OPTIONS, CSV_REQUIRED_HEADERS, CSV_OPTIONAL_HEADERS
from rezscan_app.utils.file_utils import save_uploaded_file, allowed_file
from rezscan_app.utils.logging_config import setup_logging
from datetime import datetime
import sqlite3
import logging
import csv
import io

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

residents_bp = Blueprint('residents', __name__)

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

@residents_bp.route('/residents', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def residents():
    """Render resident management page with search, sort, and pagination."""
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents route")
    
    search = request.args.get('search', '').strip()
    filter_unit = request.args.get('filterUnit', '').strip()
    filter_housing = request.args.get('filterHousing', '').strip()
    filter_level = request.args.get('filterLevel', '').strip()
    sort = request.args.get('sort', 'name')
    direction = request.args.get('direction', 'asc')
    page = int(request.args.get('page', 1)) if request.args.get('page', '1').isdigit() else 1
    per_page = 10

    # Validate filter parameters
    if filter_unit not in UNIT_OPTIONS:
        filter_unit = ''
    if filter_housing not in HOUSING_OPTIONS:
        filter_housing = ''
    if filter_level not in LEVEL_OPTIONS:
        filter_level = ''

    query = "SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR mdoc LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    if filter_unit:
        query += " AND unit = ?"
        params.append(filter_unit)
    if filter_housing:
        query += " AND housing_unit = ?"
        params.append(filter_housing)
    if filter_level:
        query += " AND level = ?"
        params.append(filter_level)

    if sort not in ['name', 'mdoc', 'level']:
        sort = 'name'
    if direction not in ['asc', 'desc']:
        direction = 'asc'

    query += f" ORDER BY {'CAST(mdoc AS INTEGER)' if sort == 'mdoc' else sort} {direction}"
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(query, params)
            columns = ['id', 'name', 'mdoc', 'unit', 'housing_unit', 'level', 'photo']
            residents = [dict(zip(columns, row)) for row in c.fetchall()]

            # Count filtered residents
            count_query = "SELECT COUNT(*) FROM residents WHERE 1=1"
            count_params = []
            if search:
                count_query += " AND (name LIKE ? OR mdoc LIKE ?)"
                count_params.extend([f'%{search}%', f'%{search}%'])
            if filter_unit:
                count_query += " AND unit = ?"
                count_params.append(filter_unit)
            if filter_housing:
                count_query += " AND housing_unit = ?"
                count_params.append(filter_housing)
            if filter_level:
                count_query += " AND level = ?"
                count_params.append(filter_level)
            c.execute(count_query, count_params)
            filtered_count = c.fetchone()[0]

            # Count total residents (unfiltered)
            c.execute("SELECT COUNT(*) FROM residents")
            total_count = c.fetchone()[0]

            # Calculate total pages
            total_pages = max((filtered_count + per_page - 1) // per_page, 1)

            logger.debug(f"User {username} fetched {len(residents)} residents (filtered: {filtered_count}, total: {total_count})")
            log_audit_action(
                username=username,
                action='view',
                target='residents',
                details=f"Viewed residents page with {len(residents)} records (filtered: {filtered_count})"
            )

    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} in residents: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents',
            details=f"Database error: {str(e)}"
        )
        flash("Database error occurred.", "error")
        return redirect(url_for('residents.residents'))

    return render_template(
        'residents/residents.html',
        residents=residents,
        search=search,
        sort=sort,
        direction=direction,
        page=page,
        total_pages=total_pages,
        filterUnit=filter_unit,
        filterHousing=filter_housing,
        filterLevel=filter_level,
        filtered_count=filtered_count,
        total_count=total_count,
        UNIT_OPTIONS=UNIT_OPTIONS,
        HOUSING_OPTIONS=HOUSING_OPTIONS,
        LEVEL_OPTIONS=LEVEL_OPTIONS
    )

@residents_bp.route('/residents/add', methods=['GET', 'POST'])
@login_required
def add_resident():
    """Add a new resident."""
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/add route, method: {request.method}")
    
    # Get mdoc from query parameter (e.g., ?mdoc=888)
    mdoc_prefill = request.args.get('mdoc', '')

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mdoc = request.form.get('mdoc', '').strip()
        unit = request.form.get('unit', '').strip()
        housing_unit = request.form.get('housing_unit', '').strip()
        level = request.form.get('level', '').strip()

        if not all([name, mdoc, unit, housing_unit, level]):
            logger.warning(f"User {username} failed to add resident: missing fields")
            log_audit_action(
                username=username,
                action='add_resident_failed',
                target='residents',
                details='Missing required fields'
            )
            flash('All fields are required.', 'warning')
            return render_template(
                'residents/add_resident.html',
                UNIT_OPTIONS=UNIT_OPTIONS,
                HOUSING_OPTIONS=HOUSING_OPTIONS,
                LEVEL_OPTIONS=LEVEL_OPTIONS,
                mdoc_prefill=mdoc  # Pass mdoc back to form if validation fails
            )

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO residents (name, mdoc, unit, housing_unit, level) VALUES (?, ?, ?, ?, ?)",
                    (name, mdoc, unit, housing_unit, level)
                )
                conn.commit()
                logger.info(f"User {username} added resident: {name} (MDOC: {mdoc})")
                log_audit_action(
                    username=username,
                    action='add_resident',
                    target='residents',
                    details=f"Added resident: {name}, MDOC: {mdoc}, Unit: {unit}, Housing: {housing_unit}, Level: {level}"
                )
                flash(f'Resident {name} added successfully!', 'success')
                return redirect(url_for('residents.residents'))
        except sqlite3.IntegrityError:
            logger.error(f"User {username} failed to add resident: MDOC {mdoc} already exists")
            log_audit_action(
                username=username,
                action='add_resident_failed',
                target='residents',
                details=f"MDOC {mdoc} already exists"
            )
            flash('Resident with this MDOC already exists.', 'warning')
        except sqlite3.Error as e:
            logger.error(f"Database error for user {username} adding resident: {str(e)}")
            log_audit_action(
                username=username,
                action='error',
                target='residents',
                details=f"Database error adding resident: {str(e)}"
            )
            flash(f'Error adding resident: {str(e)}', 'danger')

    log_audit_action(
        username=username,
        action='view',
        target='add_resident',
        details='Accessed add resident page'
    )
    return render_template(
        'residents/add_resident.html',
        UNIT_OPTIONS=UNIT_OPTIONS,
        HOUSING_OPTIONS=HOUSING_OPTIONS,
        LEVEL_OPTIONS=LEVEL_OPTIONS,
        mdoc_prefill=mdoc_prefill  # Pass mdoc to pre-fill form
    )

@residents_bp.route('/residents/edit/<int:mdoc>', methods=['GET', 'POST'], strict_slashes=False)
@login_required
@role_required('admin')
def edit_resident(mdoc):
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/edit/{mdoc} route, method: {request.method}")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM residents WHERE mdoc = ?", (mdoc,))
            resident_name = c.fetchone()
            resident_name = resident_name[0] if resident_name else 'unknown'
            if request.method == 'POST':    
                name = request.form['name'].strip()
                new_mdoc = request.form['mdoc'].strip()
                unit = request.form['unit'].strip()
                housing_unit = request.form['housing_unit'].strip()
                level = request.form['level'].strip()
                photo_file = request.files.get('photo')
                photo_path = save_uploaded_file(photo_file) or request.form.get('existing_photo')
                
                try:
                    c.execute("""
                        UPDATE residents
                        SET name = ?, mdoc = ?, unit = ?, housing_unit = ?, level = ?, photo = ?
                        WHERE mdoc = ?
                    """, (name, new_mdoc, unit, housing_unit, level, photo_path, mdoc))
                    if c.rowcount == 0:
                        logger.warning(f"User {username} failed to edit resident: MDOC {mdoc} not found")
                        log_audit_action(
                            username=username,
                            action='edit_resident_failed',
                            target='residents',
                            details=f"MDOC {mdoc} not found"
                        )
                        flash("Resident not found.", "warning")
                        return redirect(url_for('residents.residents'))
                    conn.commit()
                    logger.info(f"User {username} updated resident: {name} (MDOC: {new_mdoc})")
                    log_audit_action(
                        username=username,
                        action='edit_resident',
                        target='residents',
                        details=f"Updated resident: {name}, MDOC: {new_mdoc}, Unit: {unit}, Housing: {housing_unit}, Level: {level}"
                    )
                    flash(f"Resident {resident_name} updated successfully.", "success")
                    return redirect(url_for('residents.residents'))
                except sqlite3.IntegrityError:
                    logger.error(f"User {username} failed to edit resident: MDOC {new_mdoc} already exists")
                    log_audit_action(
                        username=username,
                        action='edit_resident_failed',
                        target='residents',
                        details=f"MDOC {new_mdoc} already exists"
                    )
                    flash("Error: MDOC must be unique.", "warning")
                    c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE mdoc = ?", (mdoc,))
                    resident = c.fetchone()
                    return render_template('residents/edit_resident.html', resident=resident,
                                        UNIT_OPTIONS=UNIT_OPTIONS, HOUSING_OPTIONS=HOUSING_OPTIONS, LEVEL_OPTIONS=LEVEL_OPTIONS)
                except sqlite3.Error as e:
                    logger.error(f"Database error for user {username} editing resident MDOC {mdoc}: {str(e)}")
                    log_audit_action(
                        username=username,
                        action='error',
                        target='residents',
                        details=f"Database error editing resident: {str(e)}"
                    )
                    flash(f"Error editing resident: {str(e)}", "danger")
                    return redirect(url_for('residents.residents'))

            c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE mdoc = ?", (mdoc,))
            resident = c.fetchone()
            if not resident:
                logger.warning(f"User {username} failed to access resident: MDOC {mdoc} not found")
                log_audit_action(
                    username=username,
                    action='view_failed',
                    target='edit_resident',
                    details=f"MDOC {mdoc} not found"
                )
                flash("Resident not found.", "warning")
                return redirect(url_for('residents.residents'))
            
            logger.debug(f"User {username} accessed edit page for resident MDOC {mdoc}")
            log_audit_action(
                username=username,
                action='view',
                target='edit_resident',
                details=f"Accessed edit page for resident MDOC {mdoc}"
            )

    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} in edit_resident: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='edit_resident',
            details=f"Database error: {str(e)}"
        )
        flash("Database error occurred.", "danger")
        return redirect(url_for('residents.residents'))

    return render_template('residents/edit_resident.html', resident=resident,
                           UNIT_OPTIONS=UNIT_OPTIONS, HOUSING_OPTIONS=HOUSING_OPTIONS, LEVEL_OPTIONS=LEVEL_OPTIONS)

@residents_bp.route('/residents/delete/<int:mdoc>', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_resident(mdoc):
    """Delete a resident by MDOC."""
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/delete/{mdoc} route")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM residents WHERE mdoc = ?", (mdoc,))
            resident_name = c.fetchone()
            resident_name = resident_name[0] if resident_name else 'unknown'
            
            c.execute("DELETE FROM residents WHERE mdoc = ?", (mdoc,))
            if c.rowcount == 0:
                logger.warning(f"User {username} failed to delete resident: MDOC {mdoc} not found")
                log_audit_action(
                    username=username,
                    action='delete_resident_failed',
                    target='residents',
                    details=f"MDOC {mdoc} not found"
                )
                flash("Resident not found.", "warning")
            else:
                conn.commit()
                logger.info(f"User {username} deleted resident: {resident_name} (MDOC: {mdoc})")
                log_audit_action(
                    username=username,
                    action='delete_resident',
                    target='residents',
                    details=f"Deleted resident: {resident_name}, MDOC: {mdoc}"
                )
                flash(f"Resident {resident_name} deleted successfully.", "success")
                
    except sqlite3.Error as e:
        logger.error(f"Error deleting resident MDOC {mdoc} for user {username}: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents',
            details=f"Database error deleting resident: {str(e)}"
        )
        flash(f"Error deleting resident: {str(e)}", "danger")
    
    return redirect(url_for('residents.residents'))

@residents_bp.route('/residents/delete_all', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def delete_all_residents():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/delete_all route")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM residents")
            deleted_rows = c.rowcount
            conn.commit()
            
            log_audit_action(
                username=username,
                action='delete_all_residents',
                target='residents',
                details=f"Deleted {deleted_rows} resident(s)"
            )
            logger.info(f"User {username} deleted {deleted_rows} resident(s)")
            logger.debug(f"Details: DELETE FROM residents executed, affected {deleted_rows} rows")
            
            if deleted_rows == 0:
                flash("No residents found to delete.", "info")
            else:
                flash(f"Successfully deleted {deleted_rows} resident(s).", "success")
                
    except sqlite3.Error as e:
        logger.error(f"Error deleting all residents for user {username}: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents',
            details=f"Database error deleting all residents: {str(e)}"
        )
        flash(f"Error deleting residents: {str(e)}", "danger")
    
    return redirect(url_for('admin.admin_dashboard'))

@residents_bp.route('/residents/export', strict_slashes=False)
@login_required
@role_required('admin')
def export_residents():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/export route")
    
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Name', 'MDOC', 'Unit', 'Housing Unit', 'Level', 'Photo'])
        
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents ORDER BY name")
            rows = c.fetchall()
            
            for row in rows:
                writer.writerow(row)
            
            logger.info(f"User {username} exported {len(rows)} resident records to CSV")
            log_audit_action(
                username=username,
                action='export',
                target='residents',
                details=f"Exported {len(rows)} resident records to CSV"
            )
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='residents.csv'
        )
    
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} during resident export: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents_export',
            details=f"Database error during export: {str(e)}"
        )
        flash("Error exporting residents.", "danger")
        return redirect(url_for('residents.residents'))
    except Exception as e:
        logger.error(f"Unexpected error for user {username} during resident export: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents_export',
            details=f"Unexpected error during export: {str(e)}"
        )
        flash("Error exporting residents.", "danger")
        return redirect(url_for('residents.residents'))

@residents_bp.route('/residents/import', methods=['GET'], strict_slashes=False)
@login_required
@role_required('admin')
def import_residents():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/import route")
    
    log_audit_action(
        username=username,
        action='view',
        target='import_residents',
        details='Accessed import residents page'
    )
    return render_template('residents/import_residents.html', 
                          CSV_REQUIRED_HEADERS=CSV_REQUIRED_HEADERS, 
                          CSV_OPTIONAL_HEADERS=CSV_OPTIONAL_HEADERS)

@residents_bp.route('/residents/import/upload', methods=['POST'], strict_slashes=False)
@login_required
@role_required('admin')
def upload_residents():
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/import/upload route")
    
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
        logger.warning(f"User {username} failed to upload residents: No file selected")
        log_audit_action(
            username=username,
            action='import_residents_failed',
            target='residents',
            details='No file selected'
        )
        return jsonify({'success': False, 'message': 'No file selected.'}), 400
    elif not allowed_file(file.filename):
        logger.warning(f"User {username} failed to upload residents: Invalid file type")
        log_audit_action(
            username=username,
            action='import_residents_failed',
            target='residents',
            details='Invalid file type; only CSV allowed'
        )
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
                logger.warning(f"User {username} skipped row in CSV import: Missing MDOC")
                continue

            # Replace multiple phrases in housing_unit
            housing_unit = row.get('housing_unit', '')
            replacements = {
                'women ctr': "Women's Center",
                'a walk': "SMWRC",
                'b walk': "SMWRC",
                'c walk': "SMWRC",
                'd walk': "SMWRC",
            }
            for key, value in replacements.items():
                if housing_unit.lower() == key:
                    row['housing_unit'] = value
                    break

            csv_data[row['mdoc']] = row

        with get_db() as conn:
            c = conn.cursor()
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
                            logger.debug(f"User {username} added resident MDOC {mdoc} during import")
                        except sqlite3.Error as e:
                            stats['failed'] += 1
                            messages.append(f"✘ Error adding {new_data['name']}: {str(e)}")
                            logger.error(f"User {username} failed to add resident MDOC {mdoc}: {str(e)}")
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
                                logger.debug(f"User {username} updated resident MDOC {mdoc} during import")
                            except sqlite3.Error as e:
                                stats['failed'] += 1
                                messages.append(f"✘ Error updating {new_data['name']}: {str(e)}")
                                logger.error(f"User {username} failed to update resident MDOC {mdoc}: {str(e)}")

            for mdoc in existing:
                if mdoc not in csv_data:
                    preview_changes.append(f"❌ Delete: {existing[mdoc]['name']}")
                    stats['deleted'] += 1
                    if not dry_run:
                        try:
                            current = existing[mdoc]
                            backup_entries.append((mdoc, current['name'], current['unit'], current['housing_unit'], current['level'], current['photo']))
                            c.execute("DELETE FROM residents WHERE mdoc = ?", (mdoc,))
                            logger.debug(f"User {username} deleted resident MDOC {mdoc} during import")
                        except sqlite3.Error as e:
                            stats['failed'] += 1
                            messages.append(f"✘ Error deleting MDOC {mdoc}: {str(e)}")
                            logger.error(f"User {username} failed to delete resident MDOC {mdoc}: {str(e)}")

            if not dry_run:
                conn.commit()
                messages.append("✅ Changes committed to database.")
                logger.info(f"User {username} committed resident import: {stats['added']} added, {stats['updated']} updated, {stats['deleted']} deleted, {stats['failed']} failed")

                # Log import to history
                try:
                    timestamp = datetime.utcnow().isoformat()
                    summary = (stats['added'], stats['updated'], stats['deleted'], stats['failed'], stats['processed'])

                    file.stream.seek(0)
                    raw_csv = file.stream.read().decode("utf-8-sig")

                    c.execute("""
                        INSERT INTO import_history (timestamp, username, added, updated, deleted, failed, total, csv_content)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (timestamp, username, *summary, raw_csv))
                    import_id = c.lastrowid

                    for b in backup_entries:
                        c.execute("""
                            INSERT INTO resident_backups (import_id, mdoc, name, unit, housing_unit, level, photo)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (import_id, *b))

                    conn.commit()
                    logger.info(f"User {username} logged import to history @ {timestamp} with {len(backup_entries)} backup(s)")
                    log_audit_action(
                        username=username,
                        action='import_residents',
                        target='residents',
                        details=f"Imported residents: {stats['added']} added, {stats['updated']} updated, {stats['deleted']} deleted, {stats['failed']} failed"
                    )
                except sqlite3.Error as e:
                    logger.error(f"User {username} failed to log import history or backups: {str(e)}")
                    log_audit_action(
                        username=username,
                        action='error',
                        target='residents_import',
                        details=f"Failed to log import history: {str(e)}"
                    )
                    messages.append(f"⚠️ Warning: Failed to log import history: {str(e)}")
            else:
                messages.append("🧪 Dry Run: No changes committed.")
                logger.info(f"User {username} performed dry run import: {stats['processed']} rows processed")

        log_audit_action(
            username=username,
            action='import_residents' if not dry_run else 'import_residents_dry_run',
            target='residents',
            details=f"Processed {stats['processed']} rows: {stats['added']} added, {stats['updated']} updated, {stats['deleted']} deleted, {stats['failed']} failed"
        )
        return jsonify({
            'success': True,
            'messages': messages,
            'stats': stats,
            'preview_changes': preview_changes,
            'update_diffs': update_diffs
        })

    except UnicodeDecodeError as e:
        logger.error(f"User {username} failed to read CSV: Invalid encoding - {str(e)}")
        log_audit_action(
            username=username,
            action='import_residents_failed',
            target='residents',
            details=f"Invalid CSV encoding: {str(e)}"
        )
        return jsonify({'success': False, 'message': f"Invalid CSV encoding: {str(e)}"}), 400
    except sqlite3.Error as e:
        logger.error(f"Database error for user {username} during resident import: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents_import',
            details=f"Database error during import: {str(e)}"
        )
        return jsonify({'success': False, 'message': f"Database error: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error for user {username} during resident import: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents_import',
            details=f"Unexpected error during import: {str(e)}"
        )
        return jsonify({'success': False, 'message': f"Error reading CSV: {str(e)}"}), 500