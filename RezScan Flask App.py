from flask import Flask, redirect, url_for
from config import Config
from models.database import init_db, init_app
import os

try:
    from routes.residents_export import residents_export_bp
    from routes.residents_import import residents_import_bp
    from routes.scanlog_export import scanlog_export_bp
    from routes.scanlog_delete import scanlog_delete_bp
    from routes.scanlog import scanlog_bp
    from routes.locations import locations_bp
    from routes.locations_delete import locations_delete_bp
    from routes.residents import residents_bp
    from routes.residents_edit import residents_edit_bp
    from routes.residents_delete import residents_delete_bp
    from routes.residents_delete_all import residents_delete_all_bp
    from routes.residents_import_sample import residents_sample_bp
    from routes.scan import scan_bp
    from routes.dashboard import dashboard_bp
    print("All Blueprints imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
    raise

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.register_blueprint(residents_export_bp)
app.register_blueprint(residents_import_bp)
app.register_blueprint(scanlog_export_bp)
app.register_blueprint(scanlog_delete_bp)
app.register_blueprint(scanlog_bp)
app.register_blueprint(locations_bp)
app.register_blueprint(locations_delete_bp)
app.register_blueprint(residents_bp)
app.register_blueprint(residents_edit_bp)
app.register_blueprint(residents_delete_bp)
app.register_blueprint(residents_delete_all_bp)
app.register_blueprint(residents_sample_bp)
app.register_blueprint(scan_bp)
app.register_blueprint(dashboard_bp)
print("All Blueprints registered successfully")

init_app(app)

@app.route('/')
def index():
    return redirect(url_for('scan.scan'))

<<<<<<< HEAD
        # Determine location from prefix
        if '-' not in raw_input:
            message = "Invalid scan format. Expected format: PREFIX-MDOC"
            return render_template('scan.html', message=message)

        prefix, mdoc = raw_input.split('-', 1)

        try:
            message = process_scan(mdoc.strip(), prefix.strip().upper())
        except Exception as e:
            message = f"Error processing scan: {str(e)}"

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
from flask import render_template
import sqlite3

@app.route('/admin/dashboard')
def dashboard():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Get latest scan per mdoc
        c.execute('''
            SELECT s.mdoc, MAX(s.date || ' ' || s.time) as latest_time
            FROM scans s
            GROUP BY s.mdoc
        ''')
        latest_scans = c.fetchall()

        # Filter only those where latest scan status is 'in' and join with residents
        checked_in = []
        for mdoc, latest_time in latest_scans:
            c.execute('''
                SELECT r.name, r.mdoc, r.unit, r.housing_unit, r.level, s.date, s.time, s.location
                FROM scans s
                JOIN residents r ON s.mdoc = r.mdoc
                WHERE s.mdoc = ? AND (s.date || ' ' || s.time) = ? AND s.status = 'In'
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
# Start Delete Location 
# ---------------------
@app.route('/admin/locations/delete/<int:location_id>', methods=['POST'])
def delete_location(location_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        conn.commit()
    flash("Location deleted successfully.", "success")
    return redirect(url_for('manage_locations'))
# -------------------
# End Delete Location 
# -------------------
# ---------------------
# Start Scan Log 
# ---------------------
@app.route('/admin/scanlog', methods=['GET', 'POST'])
def scanlog():
    # Connect to SQLite database
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
    
        # Query all data from the table
        c.execute('SELECT * FROM scans_with_residents ORDER BY time desc')
        data = c.fetchall()
    
        # Get distinct status and location options for filters
        c.execute('SELECT DISTINCT status FROM scans_with_residents ORDER BY status')
        status_options = [row[0] for row in c.fetchall() if row[0]]
        
        c.execute('SELECT DISTINCT location FROM scans_with_residents ORDER BY location')
        location_options = [row[0] for row in c.fetchall() if row[0]]
    
    # Render template with data and filter options
    return render_template('scanlog.html', scans=data, status_options=status_options, location_options=location_options)
# -------------------
# End Scan Log 
# -------------------
# ---------------------
# Start Export Scan Log
# ---------------------
@app.route('/admin/scanlog/export')
def export_scanlog():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['MDOC', 'Name', 'Date', 'Time', 'Status', 'Location'])

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM scans_with_residents ORDER BY time desc")
        for row in c.fetchall():
            writer.writerow(row)

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='scanlog.csv')
# ---------------------
# End Export Scan Log
# ---------------------

# ----------------------------------
# Start Resident Status API Endpoint
# ----------------------------------
@app.route('/api/status/<mdoc>', methods=['GET'])
def get_resident_status(mdoc):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Get resident info
        c.execute("SELECT id, name FROM residents WHERE mdoc = ?", (mdoc,))
        resident = c.fetchone()
        if not resident:
            return {
                "mdoc": mdoc,
                "status": "Not Found",
                "message": f"Resident with MDOC {mdoc} not found."
            }, 404

        resident_id, name = resident

        # Get last scan
        c.execute('''
            SELECT s.timestamp, s.direction, l.name
            FROM scans s
            JOIN locations l ON s.location_id = l.id
            WHERE s.mdoc = ?
            ORDER BY s.timestamp DESC
            LIMIT 1
        ''', (resident_id,))
        scan = c.fetchone()

        if not scan:
            return {
                "mdoc": mdoc,
                "name": name,
                "status": "No Scans Found"
            }

        timestamp, direction, location = scan

        return {
            "mdoc": mdoc,
            "name": name,
            "last_location": location,
            "last_direction": direction,
            "timestamp": timestamp,
            "status": "Scanned In" if direction == 'in' else "Scanned Out"
        }
        
# -------------------------
# Start Delete Scan Log
# -------------------------
@app.route('/admin/scanlog/delete', methods=['POST'])
def delete_scanlog():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM scans")
        conn.commit()
    return redirect(url_for('scanlog'))
# -------------------------
# End Delete All Residents
# -------------------------

# --------------------------------
# End Resident Status API Endpoint
# --------------------------------

# ---------------------
# App Entry Point
# ---------------------
=======
>>>>>>> df37e33bd4600972a226264da138a4ddd34b5f7c
if __name__ == '__main__':
    init_db()
    print(app.url_map)  # Debug: Print all registered routes
    app.run(debug=True, host='127.0.0.1', port=5080)