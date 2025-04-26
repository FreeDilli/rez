from flask import Blueprint, render_template, request, flash
from models.database import get_db
from routes.auth import login_required
import sqlite3
from utils.constants import LOCATION_TYPES  # Import the constant

locations_bp = Blueprint('locations', __name__)

@locations_bp.route('/admin/locations', methods=['GET', 'POST'], strict_slashes=False)
@login_required
def manage_locations():
    message = None
    with get_db() as conn:
        c = conn.cursor()
        if request.method == 'POST':
            name = request.form['name'].strip()
            prefix = request.form['prefix'].strip().upper()
            location_type = request.form['type'].strip()
            if not (name and prefix and location_type):
                message = "All fields are required."
            elif not prefix.isalnum():
                message = "Prefix must be alphanumeric."
            else:
                try:
                    c.execute("INSERT INTO locations (name, prefix, type) VALUES (?, ?, ?)", (name, prefix, location_type))
                    conn.commit()
                    message = f"Location '{name}' added."
                except sqlite3.IntegrityError:
                    message = "Location or prefix already exists."
        c.execute("SELECT id, name, prefix, type FROM locations ORDER BY name")
        locations = c.fetchall()
    return render_template('locations.html', locations=locations, message=message, LOCATION_TYPES=LOCATION_TYPES)