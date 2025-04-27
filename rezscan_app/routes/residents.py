from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from rezscan_app.models.database import get_db
from rezscan_app.routes.auth import login_required, role_required
from rezscan_app.utils.constants import UNIT_OPTIONS, HOUSING_OPTIONS, LEVEL_OPTIONS
from rezscan_app.utils.file_utils import save_uploaded_file
from rezscan_app.utils.logging_config import setup_logging
import sqlite3
import logging

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

@residents_bp.route('/admin/residents', methods=['GET', 'POST'], strict_slashes=False)
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

            logger.debug(f"User {username} fetched {len(residents)} residents (filtered: {filtered_count}, total: {total_count})")
            log_audit_action(
                username=username,
                action='view',
                target='residents',
                details=f"Viewed residents page with {len(residents)} records (filtered: {filtered_count})"
            )

            next_page = page + 1 if page * per_page < filtered_count else None
            prev_page = page - 1 if page > 1 else None

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
        'residents.html',
        residents=residents,
        prev_page=prev_page,
        next_page=next_page,
        search=search,
        sort=sort,
        direction=direction,
        page=page,
        filterUnit=filter_unit,
        filterHousing=filter_housing,
        filterLevel=filter_level,
        filtered_count=filtered_count,
        total_count=total_count,
        UNIT_OPTIONS=UNIT_OPTIONS,
        HOUSING_OPTIONS=HOUSING_OPTIONS,
        LEVEL_OPTIONS=LEVEL_OPTIONS
    )

@residents_bp.route('/admin/residents/add', methods=['GET', 'POST'])
@login_required
def add_resident():
    """Add a new resident."""
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/add route, method: {request.method}")
    
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
            flash('All fields are required.', 'danger')
            return redirect(url_for('residents.add_resident'))

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
                flash('Resident added successfully!', 'success')
                return redirect(url_for('residents.residents'))
        except sqlite3.IntegrityError:
            logger.error(f"User {username} failed to add resident: MDOC {mdoc} already exists")
            log_audit_action(
                username=username,
                action='add_resident_failed',
                target='residents',
                details=f"MDOC {mdoc} already exists"
            )
            flash('Resident with this MDOC already exists.', 'danger')
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
        'add_resident.html',
        UNIT_OPTIONS=UNIT_OPTIONS,
        HOUSING_OPTIONS=HOUSING_OPTIONS,
        LEVEL_OPTIONS=LEVEL_OPTIONS
    )

@residents_bp.route('/admin/residents/edit/<int:mdoc>', methods=['GET', 'POST'], strict_slashes=False)
@login_required
@role_required('admin')
def edit_resident(mdoc):
    username = current_user.username if current_user.is_authenticated else 'unknown'
    logger.debug(f"User {username} accessing /admin/residents/edit/{mdoc} route, method: {request.method}")
    
    try:
        with get_db() as conn:
            c = conn.cursor()
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
                        flash("Resident not found.", "error")
                        return redirect(url_for('residents.residents'))
                    conn.commit()
                    logger.info(f"User {username} updated resident: {name} (MDOC: {new_mdoc})")
                    log_audit_action(
                        username=username,
                        action='edit_resident',
                        target='residents',
                        details=f"Updated resident: {name}, MDOC: {new_mdoc}, Unit: {unit}, Housing: {housing_unit}, Level: {level}"
                    )
                    flash("Resident updated successfully.", "success")
                    return redirect(url_for('residents.residents'))
                except sqlite3.IntegrityError:
                    logger.error(f"User {username} failed to edit resident: MDOC {new_mdoc} already exists")
                    log_audit_action(
                        username=username,
                        action='edit_resident_failed',
                        target='residents',
                        details=f"MDOC {new_mdoc} already exists"
                    )
                    flash("Error: MDOC must be unique.", "error")
                    c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE mdoc = ?", (mdoc,))
                    resident = c.fetchone()
                    return render_template('edit_resident.html', resident=resident,
                                        UNIT_OPTIONS=UNIT_OPTIONS, HOUSING_OPTIONS=HOUSING_OPTIONS, LEVEL_OPTIONS=LEVEL_OPTIONS)
                except sqlite3.Error as e:
                    logger.error(f"Database error for user {username} editing resident MDOC {mdoc}: {str(e)}")
                    log_audit_action(
                        username=username,
                        action='error',
                        target='residents',
                        details=f"Database error editing resident: {str(e)}"
                    )
                    flash(f"Error editing resident: {str(e)}", "error")
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
                flash("Resident not found.", "error")
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
        flash("Database error occurred.", "error")
        return redirect(url_for('residents.residents'))

    return render_template('edit_resident.html', resident=resident,
                           UNIT_OPTIONS=UNIT_OPTIONS, HOUSING_OPTIONS=HOUSING_OPTIONS, LEVEL_OPTIONS=LEVEL_OPTIONS)

@residents_bp.route('/admin/residents/delete/<int:mdoc>', methods=['POST'], strict_slashes=False)
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
                flash("Resident not found.", "error")
            else:
                conn.commit()
                logger.info(f"User {username} deleted resident: {resident_name} (MDOC: {mdoc})")
                log_audit_action(
                    username=username,
                    action='delete_resident',
                    target='residents',
                    details=f"Deleted resident: {resident_name}, MDOC: {mdoc}"
                )
                flash("Resident deleted successfully.", "success")
                
    except sqlite3.Error as e:
        logger.error(f"Error deleting resident MDOC {mdoc} for user {username}: {str(e)}")
        log_audit_action(
            username=username,
            action='error',
            target='residents',
            details=f"Database error deleting resident: {str(e)}"
        )
        flash(f"Error deleting resident: {str(e)}", "error")
    
    return redirect(url_for('residents.residents'))

@residents_bp.route('/admin/residents/delete_all', methods=['POST'], strict_slashes=False)
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
        flash(f"Error deleting residents: {str(e)}", "error")
    
    return redirect(url_for('residents.residents'))