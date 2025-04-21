from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.database import get_db
import sqlite3
import os
from werkzeug.utils import secure_filename

residents_bp = Blueprint('residents', __name__)

@residents_bp.route('/admin/residents', methods=['GET', 'POST'], strict_slashes=False)
def manage_residents():
    message = None
    unit_options = ["Unit 1", "Unit 2", "Unit 3", "MPU", "SMWRC"]
    housing_options = [
        "Delta", "Echo", "Foxtrot", "Dorm 5", "Dorm 6",
        "Women's Center", "A Pod", "B North", "B South",
        "B Ad North", "B Ad South", "C North", "C South", "C Center", "SMWRC"
    ]
    level_options = ["1", "2", "3", "4"]
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
                photo_path = ""
                if photo_file and photo_file.filename:
                    filename = secure_filename(photo_file.filename)
                    filepath = os.path.join('static/uploads', filename)
                    photo_file.save(filepath)
                    photo_path = os.path.join('static', 'uploads', filename).replace("\\", "/")
                else:
                    photo_path = request.form.get('photo', '').strip()
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
                           unit_options=unit_options, housing_options=housing_options, level_options=level_options)