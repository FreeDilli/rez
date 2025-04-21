# Utils/scan_logic.py
import sqlite3
from datetime import datetime

DB_PATH = 'rezscan.db'  # Default for testing

def insert_scan_sqlite(mdoc, location):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            # Get location ID
            c.execute("SELECT id FROM locations WHERE name = ?", (location,))
            loc = c.fetchone()
            if not loc:
                raise ValueError(f"Location '{location}' not found.")

            location_id = loc[0]

            # Insert 'out' scan if the last was 'in'
            c.execute("""
                SELECT location_id FROM scans
                WHERE mdoc = ? AND direction = 'in'
                ORDER BY timestamp DESC LIMIT 1
            """, (mdoc,))
            active = c.fetchone()
            if active:
                c.execute("INSERT INTO scans (mdoc, timestamp, location_id, direction) VALUES (?, ?, ?, 'out')",
                          (mdoc, datetime.now().isoformat(), active[0]))

            # Insert 'in' scan
            c.execute("INSERT INTO scans (mdoc, timestamp, location_id, direction) VALUES (?, ?, ?, 'in')",
                      (mdoc, datetime.now().isoformat(), location_id))
            conn.commit()
        return True

    except Exception as e:
        print(f"SQLite Scan Insert Error: {e}")
        return False


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
