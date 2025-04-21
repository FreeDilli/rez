import sqlite3
from datetime import datetime

DB_PATH = 'rezscan.db'

def process_scan(mdoc, prefix):
    location_name = get_location_name_by_prefix(prefix)
    if not location_name:
        return f"Prefix '{prefix}' not associated with any location."

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Get resident ID from mdoc
        c.execute("SELECT id FROM residents WHERE mdoc = ?", (mdoc,))
        res = c.fetchone()
        if not res:
            return f"Resident with MDOC '{mdoc}' not found."

        resident_id = res[0]

        # Get location ID
        c.execute("SELECT id FROM locations WHERE prefix = ?", (prefix,))
        loc = c.fetchone()
        if not loc:
            return f"Location with prefix '{prefix}' not found."

        location_id = loc[0]

        # Check last scan
        c.execute('''
            SELECT location_id, direction, timestamp FROM scans
            WHERE mdoc = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (resident_id,))
        last_scan = c.fetchone()

        now = datetime.now().isoformat()

        if last_scan:
            last_location_id, last_direction, last_time = last_scan

            # Flag if last scan was "in" and no "out" occurred
            if last_direction == 'in' and last_location_id != location_id:
                # Missed scan (flag it)
                c.execute("""
                    INSERT INTO scans (mdoc, timestamp, location_id, direction)
                    VALUES (?, ?, ?, ?)
                """, (resident_id, now, location_id, 'in'))
                conn.commit()
                return f"⚠️ Missed scan detected (no 'out' at last location). New 'in' at {location_name} recorded."

            elif last_location_id == location_id:
                # Same location: toggle direction
                new_direction = 'out' if last_direction == 'in' else 'in'
                c.execute("""
                    INSERT INTO scans (mdoc, timestamp, location_id, direction)
                    VALUES (?, ?, ?, ?)
                """, (resident_id, now, location_id, new_direction))
                conn.commit()
                return f"{new_direction.capitalize()} scan recorded at {location_name}."

        # Default: new 'in' scan
        c.execute("""
            INSERT INTO scans (mdoc, timestamp, location_id, direction)
            VALUES (?, ?, ?, 'in')
        """, (resident_id, now, location_id))
        conn.commit()
        return f"In scan recorded at {location_name}."

def get_location_name_by_prefix(prefix):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM locations WHERE prefix = ?", (prefix,))
        row = c.fetchone()
        return row[0] if row else None



# For future SQL Server use:
# def insert_scan_sqlserver(mdoc, location, device_name, connection_string):
#     import pyodbc
#     from datetime import datetime
#     try:
#         conn = pyodbc.connect(connection_string)
#         cursor = conn.cursor()
#         cursor.execute("{CALL Insert_Scanner (?, ?, ?, ?, ?, ?, ?, ?)}", (
#             mdoc,
#             datetime.now().strftime('%Y-%m-%d'),
#             datetime.now().strftime('%H:%M:%S'),
#             "",  # Status
#             location,
#             "Scanner",
#             "DEDICATED_SCANNER",
#             device_name
#         ))
#         conn.commit()
#         return True
#     except Exception as e:
#         print("SQL Server Scan Insert Error:", e)
#         return False
#     finally:
#         cursor.close()
#         conn.close()
