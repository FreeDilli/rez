from flask import Blueprint, jsonify
from models.database import get_db

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/status/<mdoc>', methods=['GET'])
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
