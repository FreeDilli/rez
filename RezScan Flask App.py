from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime
import sqlite3
import os
from werkzeug.utils import secure_filename
import csv
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key'

DB_PATH = 'rezscan.db'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------------
# Database Setup
# ---------------------
def init_db():
    print("DB path:", os.path.abspath(DB_PATH))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mdoc TEXT UNIQUE NOT NULL,
                unit TEXT,
                housing_unit TEXT,
                level TEXT,
                photo TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                prefix TEXT UNIQUE,
                type TEXT 
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdoc INTEGER,
                timestamp TEXT,
                location_id INTEGER,
                direction TEXT CHECK(direction IN ('in', 'out')),
                FOREIGN KEY(mdoc) REFERENCES residents(id),
                FOREIGN KEY(location_id) REFERENCES locations(id)
            )
        ''')
        conn.commit()
        
# ---------------------
# End Database Setup
# ---------------------

# ---------------------
# Start Routes
# ---------------------

# ---------------------
# Start Scan Page
# ---------------------

@app.route('/')
def index():
    return redirect(url_for('scan'))

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    message = None
    if request.method == 'POST':
        raw_input = request.form['mdoc'].strip()
        if raw_input.startswith('EDU-'):
            location = 'Education'
            mdoc = raw_input.replace('EDU-', '', 1)
        elif raw_input.startswith('ACT-'):
            location = 'Activities'
            mdoc = raw_input.replace('ACT-', '', 1)
        else:
            message = "Invalid prefix or unrecognized scanner."
            return render_template('scan.html', message=message)

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM residents WHERE mdoc = ?", (mdoc,))
            res = c.fetchone()
            if not res:
                message = f"Resident with mdoc {mdoc} not found."
            else:
                mdoc = res[0]
                c.execute("SELECT id FROM locations WHERE name = ?", (location,))
                loc = c.fetchone()
                if not loc:
                    message = f"Location '{location}' not found."
                else:
                    location_id = loc[0]
                    c.execute("""
                        SELECT location_id FROM scans
                        WHERE mdoc = ? AND direction = 'in'
                        ORDER BY timestamp DESC LIMIT 1
                    """, (mdoc,))
                    active = c.fetchone()
                    if active:
                        c.execute("INSERT INTO scans (mdoc, timestamp, location_id, direction) VALUES (?, ?, ?, 'out')",
                                  (mdoc, datetime.now().isoformat(), active[0]))
                    c.execute("INSERT INTO scans (mdoc, timestamp, location_id, direction) VALUES (?, ?, ?, 'in')",
                              (mdoc, datetime.now().isoformat(), location_id))
                    message = f"{location} scan recorded for resident {mdoc}."
            conn.commit()

    return render_template('scan.html', message=message)
# ---------------------
# End Scan Page
# ---------------------

# ---------------------
# Start Residents Page
# ---------------------
@app.route('/admin/residents', methods=['GET', 'POST'])
def manage_residents():
    message = None
    unit_options = ["Unit 1", "Unit 2", "Unit 3", "MPU", "SMWRC"]
    housing_options = [
        "Delta", "Echo", "Foxtrot", "Dorm 5", "Dorm 6",
        "Women's Center", "A Pod", "B North", "B South",
        "B Ad North", "B Ad South", "C North", "C South", "C Center", "SMWRC"
    ]
    level_options = ["1", "2", "3", "4"]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            if 'bulk_delete' in request.form:
                ids_to_delete = request.form.getlist('selected')
                c.executemany("DELETE FROM residents WHERE id = ?", [(rid,) for rid in ids_to_delete])
                conn.commit()
                return redirect(url_for('manage_residents'))
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
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    photo_file.save(filepath)
                    photo_path = os.path.join('static', 'uploads', filename).replace("\\", "/")
                else:
                    photo_path = request.form.get('photo', '').strip()

                try:
                    c.execute("INSERT INTO residents (name, mdoc, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                              (name, mdoc, unit, housing_unit, level, photo_path))
                    conn.commit()
                    message = "Resident added successfully."
                except sqlite3.IntegrityError:
                    message = "Error: mdoc must be unique."

        c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents ORDER BY name")
        residents = c.fetchall()

    return render_template('residents.html', residents=residents, message=message,
                           unit_options=unit_options, housing_options=housing_options, level_options=level_options)
# ---------------------
# End Residents Page
# ---------------------
# ---------------------
# Start Edit Residents Page
# ---------------------
@app.route('/admin/residents/edit/<int:mdoc>', methods=['GET', 'POST'])
def edit_resident(mdoc):
    unit_options = ["Unit 1", "Unit 2", "Unit 3", "MPU", "SMWRC"]
    housing_options = [
        "Delta", "Echo", "Foxtrot", "Dorm 5", "Dorm 6",
        "Women's Center", "A Pod", "B North", "B South",
        "B Ad North", "B Ad South", "C North", "C South", "C Center", "SMWRC"
    ]
    level_options = ["1", "2", "3", "4"]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            name = request.form['name'].strip()
            new_mdoc = request.form['mdoc'].strip()  # New mdoc value from the form
            unit = request.form['unit'].strip()
            housing_unit = request.form['housing_unit'].strip()
            level = request.form['level'].strip()
            photo_file = request.files.get('photo')
            photo_path = request.form.get('existing_photo')

            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo_file.save(filepath)
                photo_path = os.path.join('static', 'uploads', filename).replace("\\", "/")

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
                # Re-fetch resident for re-rendering the form
                c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE id = ?", (mdoc,))
                resident = c.fetchone()
                return render_template('edit_resident.html', resident=resident,
                                       unit_options=unit_options, housing_options=housing_options, level_options=level_options)

            return redirect(url_for('manage_residents'))

        # Fetch resident by id
        c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents WHERE id = ?", (mdoc,))
        resident = c.fetchone()
        if not resident:
            flash("Resident not found.", "error")
            return redirect(url_for('manage_residents'))

    return render_template('edit_resident.html', resident=resident,
                           unit_options=unit_options, housing_options=housing_options, level_options=level_options)
# ---------------------
# End Edit Residents Page
# ---------------------
# ---------------------
# Start Delete Resident
# ---------------------
@app.route('/admin/residents/delete/<int:mdoc>', methods=['POST'])
def delete_resident(mdoc):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM residents WHERE id = ?", (mdoc,))
        conn.commit()
        flash("Resident deleted successfully.", "success")
    return redirect(url_for('manage_residents'))
# ---------------------
# End Delete Resident
# ---------------------
# -------------------------
# Start Delete All Residents
# -------------------------
@app.route('/admin/residents/delete_all', methods=['POST'])
def delete_all_residents():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM residents")
        conn.commit()
    return redirect(url_for('manage_residents'))
# -------------------------
# End Delete All Residents
# -------------------------
# ---------------------
# Start Export Residents
# ---------------------
@app.route('/admin/residents/export')
def export_residents():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'mdoc', 'unit', 'Housing Unit', 'Level', 'Photo'])

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, mdoc, unit, housing_unit, level, photo FROM residents ORDER BY name")
        for row in c.fetchall():
            writer.writerow(row)

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='residents.csv')
# ---------------------
# End Export Residents
# ---------------------

# ---------------------
# Start Import Residents
# ---------------------
@app.route('/admin/residents/import', methods=['GET', 'POST'])
def import_residents():
    messages = []
    import_count = 0  # Initialize counter for successful imports
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            messages.append("Invalid or missing CSV file.")
        else: 
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
            reader = csv.DictReader(stream)
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                # Truncate the residents table before import
                c.execute("DELETE FROM residents")
                conn.commit()
                for row in reader:
                    try:
                        c.execute("INSERT INTO residents (name, mdoc, unit, housing_unit, level, photo) VALUES (?, ?, ?, ?, ?, ?)",
                                  (row['name'], row['mdoc'], row['unit'], row['housing_unit'], row['level'], row.get('photo', '')))
                        import_count += 1  # Increment counter on successful import
                        conn.commit()
                        messages.append(f"✔ Imported {row['name']}")
                    except Exception as e:
                        messages.append(f"✘ Error on {row.get('name', 'Unknown')}: {str(e)}")

    return render_template('import_residents.html', messages=messages, import_count=import_count)
# ---------------------
# End Import Residents
# ---------------------

# ---------------------
# Start Sample Residents CSV
# ---------------------
@app.route('/admin/residents/sample')
def sample_csv():
    sample = io.StringIO()
    writer = csv.writer(sample)
    writer.writerow(['name', 'mdoc', 'unit', 'housing_unit', 'level', 'photo'])
    writer.writerow(['John Doe', '1001', 'Unit 1', 'Delta', '1', ''])
    writer.writerow(['Jane Smith', '1002', 'Unit 2', 'Dorm 5', '2', ''])
    sample.seek(0)
    return send_file(io.BytesIO(sample.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='sample_residents.csv')
# ---------------------
# End Sample Residents CSV
# ---------------------
# ---------------------
# Start Admin Dashboard Page
# ---------------------
@app.route('/admin/dashboard')
def dashboard():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Get latest scan per resident
        c.execute('''
            SELECT s.mdoc, MAX(s.timestamp)
            FROM scans s
            GROUP BY s.mdoc
        ''')
        latest_scans = c.fetchall()

        # Filter only those where latest scan is 'in'
        checked_in = []
        for mdoc, latest_time in latest_scans:
            c.execute('''
                SELECT r.name, r.mdoc, r.unit, r.housing_unit, r.level, l.name, s.timestamp
                FROM scans s
                JOIN residents r ON s.mdoc = r.id
                JOIN locations l ON s.location_id = l.id
                WHERE s.mdoc = ? AND s.timestamp = ? AND s.direction = 'in'
            ''', (mdoc, latest_time))
            result = c.fetchone()
            if result:
                checked_in.append(result)

    return render_template('dashboard.html', data=checked_in)
# -----------------------
# End Admin Dashboard Page
# -----------------------

# -------------------------
# Start Location Management
# -------------------------
@app.route('/admin/locations', methods=['GET', 'POST'])
def manage_locations():
    message = None
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            name = request.form['name'].strip()
            prefix = request.form['prefix'].strip()
            location_type = request.form['type'].strip()
            try:
                c.execute("INSERT INTO locations (name, prefix, type) VALUES (?, ?, ?)", (name, prefix, location_type))
                conn.commit()
                message = f"Location '{name}' added."
            except sqlite3.IntegrityError:
                message = f"Location or prefix already exists."

        c.execute("SELECT id, name, prefix, type FROM locations ORDER BY name")
        locations = c.fetchall()
    return render_template('locations.html', locations=locations, message=message)

# -----------------------
# End Location Management
# -----------------------

# ---------------------
# App Entry Point
# ---------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5080)
