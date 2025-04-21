from flask import Blueprint, render_template, request
from models.database import get_db

locations_bp = Blueprint('locations', __name__)

@locations_bp.route('/admin/locations', methods=['GET', 'POST'], strict_slashes=False)
def manage_locations():
    message = None
    with get_db() as conn:
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