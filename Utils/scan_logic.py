import sqlite3
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = 'rezscan.db'

def process_scan(mdoc, prefix):
    """Process a barcode scan and insert into scanstest table."""
    try:
        location_name = get_location_name_by_prefix(prefix)
        if not location_name:
            logging.warning(f"Prefix '{prefix}' not found.")
            return f"Prefix '{prefix}' not associated with any location."

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            # Validate resident
            c.execute("SELECT id FROM residents WHERE mdoc = ?", (mdoc,))
            resident = c.fetchone()
            if not resident:
                logging.warning(f"Resident with MDOC '{mdoc}' not found.")
                return f"Resident with MDOC '{mdoc}' not found."

            # Check last scan
            c.execute('''
                SELECT location, status, date || ' ' || time AS timestamp
                FROM scanstest
                WHERE mdoc = ?
                ORDER BY datetime(timestamp) DESC LIMIT 1
            ''', (mdoc,))
            last_scan = c.fetchone()

            now = datetime.now()
            scan_time = now
            out_time = now - timedelta(seconds=1)  # 1 second earlier for Out scan

            if last_scan:
                last_location, last_status, _ = last_scan

                if last_status == 'In' and last_location != location_name:
                    # Missed scan: insert 'Out' for last location, 'In' for new
                    insert_scan(c, mdoc, out_time, 'Out', last_location)
                    insert_scan(c, mdoc, scan_time, 'In', location_name)
                    conn.commit()
                    logging.info(f"Missed scan corrected for MDOC {mdoc}: Out at {last_location}, In at {location_name}.")
                    return f"Missed scan corrected: 'Out' recorded at {last_location}, new 'In' at {location_name}."

                if last_location == location_name:
                    # Same location: toggle status
                    status = 'Out' if last_status == 'In' else 'In'
                    insert_scan(c, mdoc, scan_time, status, location_name)
                    conn.commit()
                    logging.info(f"Scan recorded for MDOC {mdoc}: {status} at {location_name}.")
                    return f"{status.capitalize()} scan recorded at {location_name}."

            # Default: new 'In' scan
            insert_scan(c, mdoc, scan_time, 'In', location_name)
            conn.commit()
            logging.info(f"New In scan recorded for MDOC {mdoc} at {location_name}.")
            return f"In scan recorded at {location_name}."

    except sqlite3.Error as e:
        logging.error(f"Database error processing scan for MDOC {mdoc}: {str(e)}")
        return f"Database error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error processing scan for MDOC {mdoc}: {str(e)}")
        return f"Error processing scan: {str(e)}"

def insert_scan(cursor, mdoc, timestamp, status, location):
    """Insert a scan record into scanstest."""
    date_str = timestamp.strftime('%Y-%m-%d')
    time_str = timestamp.strftime('%H:%M:%S')
    cursor.execute("""
        INSERT INTO scanstest (mdoc, date, time, status, location)
        VALUES (?, ?, ?, ?, ?)
    """, (mdoc, date_str, time_str, status, location))

def get_location_name_by_prefix(prefix):
    """Get location name by prefix (case-insensitive)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM locations WHERE UPPER(prefix) = UPPER(?)", (prefix,))
            row = c.fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        logging.error(f"Error querying location for prefix '{prefix}': {str(e)}")
        return None