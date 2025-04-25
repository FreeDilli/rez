from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import get_db
import sqlite3
from routes.auth import login_required
from utils.constants import UNIT_OPTIONS, HOUSING_OPTIONS, LEVEL_OPTIONS
from utils.file_utils import save_uploaded_file

residents_bp = Blueprint('residents', __name__)

@residents_bp.route('/admin/residents', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def manage_residents():
    message = None
    with get_db() as conn:
        c = conn.cursor()
        if request.method == 'POST':
            if 'bulk_delete' in request.form:
                ids_to_delete = request.form.getlist('selected')
                c.executemany("DELETE FROM residents WHERE id = ?", [(rid,) for rid in ids_to_delete])
                conn.commit()
                return redirect(url_for('residents.manage_residents'))
            else:
                name = request.form['name'].strip()
                mdoc = request.form['mdoc'].strip()
                unit = request.form['unit'].strip()
                housing_unit = request.form['housing_unit'].strip()
                level = request.form['level'].strip()
                photo_file = request.files.get('photo')
                photo_path = save_uploaded_file(photo_file) or request.form.get('photo', '').strip()
                try:
                    c.execute("INSERT INTO residents (name, mdoc, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                              (name, mdoc, unit, housing_unit, level, photo_path))
                    conn.commit()
                    flash("Resident added successfully.", "success")
                except sqlite3.IntegrityError:
                    flash("Error: MDOC must be unique.", "error")
        c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents ORDER BY name")
        residents = c.fetchall()
    return render_template('residents.html', residents=residents, message=message,
                           unit_options=UNIT_OPTIONS, housing_options=HOUSING_OPTIONS, level_options=LEVEL_OPTIONS)