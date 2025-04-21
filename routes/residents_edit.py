from flask import Blueprint, render_template, request, redirect, url_for, flash
from config import Config
import sqlite3
from werkzeug.utils import secure_filename
import os

residents_edit_bp = Blueprint('residents_edit', __name__)

@residents_edit_bp.route('/admin/residents/edit/<int:mdoc>', methods=['GET', 'POST'], strict_slashes=False)
def edit_resident(mdoc):
    unit_options = ["Unit 1", "Unit 2", "Unit 3", "MPU", "SMWRC"]
    housing_options = [
        "Delta", "Echo", "Foxtrot", "Dorm 5", "Dorm 6",
        "Women's Center", "A Pod", "B North", "B South",
        "B Ad North", "B Ad South", "C North", "C South", "C Center", "SMWRC"
    ]
    level_options = ["1", "2", "3", "4"]
    with sqlite3.connect(Config.DB_PATH) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            name = request.form['name'].strip()
            new_mdoc = request.form['mdoc'].strip()
            unit = request.form['unit'].strip()
            housing_unit = request.form['housing_unit'].strip()
            level = request.form['level'].strip()
            photo_file = request.files.get('photo')
            photo_path = request.form.get('existing_photo')
            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                photo_file.save(filepath)
                photo_path = os.path.join('static', 'Uploads', filename).replace("\\", "/")
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
                                       unit_options=unit_options, housing_options=housing_options, level_options=level_options)
            return redirect(url_for('residents.manage_residents'))
        c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE id = ?", (mdoc,))
        resident = c.fetchone()
        if not resident:
            flash("Resident not found.", "error")
            return redirect(url_for('residents.manage_residents'))
    return render_template('edit_resident.html', resident=resident,
                           unit_options=unit_options, housing_options=housing_options, level_options=level_options)