from flask import Blueprint, jsonify
from rezscan_app.models.database import get_db
from flask import request

api_bp = Blueprint('api', __name__)

@api_bp.route('/admin/api/status/<mdoc>', methods=['GET'])
def get_resident_status(mdoc):
    db = get_db()
    c = db.cursor()

    # Get resident info
    c.execute("SELECT id, name FROM residents WHERE mdoc = ?", (mdoc,))
    resident = c.fetchone()
    if not resident:
        return jsonify({
            "mdoc": mdoc,
            "status": "Not Found",
            "message": f"Resident with MDOC {mdoc} not found."
        }), 404

    resident_id, name = resident

    # Get last scan for resident
    c.execute('''
        SELECT date, time, status, location
        FROM scans
        WHERE mdoc = ?
        ORDER BY scanid DESC
        LIMIT 1
    ''', (mdoc,))
    scan = c.fetchone()

    if not scan:
        return jsonify({
            "mdoc": mdoc,
            "name": name,
            "status": "No Scans Found"
        })

    date, time, status, location = scan

    return jsonify({
        "mdoc": mdoc,
        "name": name,
        "last_location": location,
        "last_status": status,
        "timestamp": f"{date} {time}",
        "status": "Scanned In" if status == 'in' else "Scanned Out"
    })

@api_bp.route('/admin/api/scan', methods=['POST'])
def api_scan():
    db = get_db()
    c = db.cursor()

    data = request.get_json()

    mdoc = data.get('mdoc')
    location = data.get('location')
    direction = data.get('direction')  # "in" or "out"

    if not all([mdoc, location, direction]):
        return jsonify({
            "status": "error",
            "message": "Missing required fields: mdoc, location, direction."
        }), 400

    # Check if resident exists
    c.execute("SELECT name FROM residents WHERE mdoc = ?", (mdoc,))
    resident = c.fetchone()

    if not resident:
        return jsonify({
            "status": "error",
            "message": f"Resident with MDOC {mdoc} not found."
        }), 404

    name = resident['name']

    # Insert scan record
    from datetime import datetime
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    c.execute('''
        INSERT INTO scans (mdoc, name, location, status, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (mdoc, name, location, direction, date, time))
    db.commit()

    return jsonify({
        "status": "success",
        "message": f"Scan recorded: {name} - {direction.upper()} at {location}.",
        "timestamp": f"{date} {time}"
    }), 201
