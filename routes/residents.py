from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import get_db
from flask_login import login_required, current_user
from utils.constants import (
    UNIT_OPTIONS, HOUSING_OPTIONS, LEVEL_OPTIONS
)
from utils.file_utils import save_uploaded_file
import sqlite3

residents_bp = Blueprint('residents', __name__)

@residents_bp.route('/admin/residents', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def residents():
    """Resident management page with search, sort, and pagination."""
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'name')
    direction = request.args.get('direction', 'asc')
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    per_page = 10

    query = "SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents"
    params = []

    if search:
        query += " WHERE name LIKE ? OR mdoc LIKE ?"
        params += [f'%{search}%', f'%{search}%']

    if sort not in ['name', 'mdoc', 'level']:
        sort = 'name'
    if direction not in ['asc', 'desc']:
        direction = 'asc'

    # Handle sorting for mdoc numerically
    if sort == 'mdoc':
        query += f" ORDER BY CAST(mdoc AS INTEGER) {direction}"
    else:
        query += f" ORDER BY {sort} {direction}"

    query += " LIMIT ? OFFSET ?"
    params += [per_page, (page - 1) * per_page]

    with get_db() as conn:
        c = conn.cursor()
        c.execute(query, params)
        residents = c.fetchall()

        # Count total matching results
        count_query = "SELECT COUNT(*) FROM residents"
        count_params = []

        if search:
            count_query += " WHERE name LIKE ? OR mdoc LIKE ?"
            count_params += [f'%{search}%', f'%{search}%']

        c.execute(count_query, count_params)
        total_count = c.fetchone()[0]

        next_page = page + 1 if page * per_page < total_count else None
        prev_page = page - 1 if page > 1 else None

    return render_template(
        'residents.html',
        residents=residents,
        prev_page=prev_page,
        next_page=next_page,
        search=search,
        sort=sort,
        direction=direction,
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

        if not name or not mdoc or not unit or not housing_unit or not level:
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

    return render_template('add_resident.html', 
                          UNIT_OPTIONS=UNIT_OPTIONS, 
                          HOUSING_OPTIONS=HOUSING_OPTIONS, 
                          LEVEL_OPTIONS=LEVEL_OPTIONS)