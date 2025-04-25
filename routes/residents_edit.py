from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import get_db
import sqlite3
from routes.auth import login_required, role_required
from utils.constants import UNIT_OPTIONS, HOUSING_OPTIONS, LEVEL_OPTIONS
from utils.file_utils import save_uploaded_file

residents_edit_bp = Blueprint('residents_edit', __name__)

@residents_edit_bp.route('/admin/residents/edit/<int:mdoc>', methods=['GET', 'POST'], strict_slashes=False)
@login_required
@role_required('admin')
def edit_resident(mdoc):
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
                    WHERE id = ?
                """, (name, new_mdoc, unit, housing_unit, level, photo_path, mdoc))
                conn.commit()
                flash("Resident updated successfully.", "success")
            except sqlite3.IntegrityError:
                flash("Error: MDOC must be unique.", "error")
                c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE id = ?", (mdoc,))
                resident = c.fetchone()
                return render_template('edit_resident.html', resident=resident,
                                       unit_options=UNIT_OPTIONS, housing_options=HOUSING_OPTIONS, level_options=LEVEL_OPTIONS)
            return redirect(url_for('residents.manage_residents'))
        c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE id = ?", (mdoc,))
        resident = c.fetchone()
        if not resident:
            flash("Resident not found.", "error")
            return redirect(url_for('residents.manage_residents'))
    return render_template('edit_resident.html', resident=resident,
                           unit_options=UNIT_OPTIONS, housing_options=HOUSING_OPTIONS, level_options=LEVEL_OPTIONS)