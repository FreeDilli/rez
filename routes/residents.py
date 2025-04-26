from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import get_db
from flask_login import login_required, current_user
from utils.constants import UNIT_OPTIONS, HOUSING_OPTIONS, LEVEL_OPTIONS
from utils.file_utils import save_uploaded_file
import sqlite3

residents_bp = Blueprint('residents', __name__)

@residents_bp.route('/admin/residents', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def residents():
    """Render resident management page with search, sort, and pagination."""
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

        next_page = page + 1 if page * per_page < filtered_count else None
        prev_page = page - 1 if page > 1 else None

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
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mdoc = request.form.get('mdoc', '').strip()
        unit = request.form.get('unit', '').strip()
        housing_unit = request.form.get('housing_unit', '').strip()
        level = request.form.get('level', '').strip()

        if not all([name, mdoc, unit, housing_unit, level]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('residents.add_resident'))

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO residents (name, mdoc, unit, housing_unit, level) VALUES (?, ?, ?, ?, ?)",
                    (name, mdoc, unit, housing_unit, level)
                )
                conn.commit()
                flash('Resident added successfully!', 'success')
                return redirect(url_for('residents.residents'))
        except sqlite3.IntegrityError:
            flash('Resident with this MDOC already exists.', 'danger')
        except Exception as e:
            flash(f'Error adding resident: {e}', 'danger')

    return render_template(
        'add_resident.html',
        UNIT_OPTIONS=UNIT_OPTIONS,
        HOUSING_OPTIONS=HOUSING_OPTIONS,
        LEVEL_OPTIONS=LEVEL_OPTIONS
    )