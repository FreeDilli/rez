import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional
from rezscan_app.config import Config
from rezscan_app.utils.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

TOO_SOON_SECONDS = 1  # configurable scan cooldown

def process_scan(mdoc: str, prefix: str) -> str:
    """
    Process a barcode scan and insert into scans table.

    Args:
        mdoc: The resident's MDOC identifier.
        prefix: The location prefix.

    Returns:
        A message indicating the result of the scan operation.
    """
    try:
        if not mdoc or not prefix:
            logger.warning(f"Invalid input: mdoc='{mdoc}', prefix='{prefix}'")
            return "Invalid input: MDOC and prefix cannot be empty."

        location_name = get_location_name_by_prefix(prefix)
        if not location_name:
            logger.warning(f"Prefix '{prefix}' not found")
            return f"Prefix '{prefix}' not associated with any location."

        with sqlite3.connect(Config.DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM residents WHERE mdoc = ?", (mdoc,))
            resident = cursor.fetchone()
            resident_not_found = not resident
            if resident_not_found:
                cursor.execute("""
                INSERT INTO residents (mdoc, name)
                VALUES (?, ?)
            """, (mdoc, "Update Resident"))
            logger.info(f"Added unknown resident with MDOC '{mdoc}' to database.")

            cursor.execute("""
                SELECT location, status, timestamp
                FROM scans
                WHERE mdoc = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (mdoc,))
            last_scan = cursor.fetchone()
            
            now = datetime.now()
            scan_time = now
            out_time = now - timedelta(seconds=1)

            if last_scan:
                last_location, last_status, last_timestamp = last_scan
                last_timestamp = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")

                if (now - last_timestamp).total_seconds() < TOO_SOON_SECONDS:
                    logger.info(f"Ignored rapid scan for MDOC '{mdoc}' at {location_name}")
                    return f"Scan ignored: too soon since last scan."

                if last_status == 'In' and last_location != location_name:
                    # Missed Out scan — record Out for last location, then In for current
                    insert_scan(cursor, mdoc, out_time, 'Out', last_location)
                    insert_scan(cursor, mdoc, scan_time, 'In', location_name)
                    conn.commit()
                    message = f"Scan recorded: 'Out' at {last_location}, 'In' at {location_name} (missed scan corrected)"
                    logger.info(f"Missed scan corrected for MDOC '{mdoc}': Out at {last_location}, In at {location_name}")
                    return _format_return_message(message, resident_not_found)

                if last_location == location_name:
                    # Same location, toggle In/Out
                    status = 'Out' if last_status == 'In' else 'In'
                    insert_scan(cursor, mdoc, scan_time, status, location_name)
                    conn.commit()
                    message = f"Scan recorded: '{status}' at {location_name}"
                    logger.info(f"Toggled scan for MDOC '{mdoc}': {status} at {location_name}")
                    return _format_return_message(message, resident_not_found)

            # Default to 'In'
            insert_scan(cursor, mdoc, scan_time, 'In', location_name)
            conn.commit()
            message = f"Scan recorded: 'In' at {location_name}"
            if resident_not_found:
                message += f" Unknown resident with MDOC '{mdoc}' added to database."
            logger.info(f"Initial scan for MDOC '{mdoc}': In at {location_name}")
            return _format_return_message(message, resident_not_found)

    except sqlite3.Error as e:
        logger.error(f"Database error during scan for MDOC '{mdoc}': {e}")
        return f"Database error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during scan for MDOC '{mdoc}': {e}")
        return f"Unexpected error: {str(e)}"

def insert_scan(cursor: sqlite3.Cursor, mdoc: str, timestamp: datetime, status: str, location: str) -> None:
    """
    Insert a scan record into the scans table.

    Args:
        cursor: Database cursor.
        mdoc: The resident's MDOC identifier.
        timestamp: The timestamp of the scan.
        status: The scan status ('In' or 'Out').
        location: The location name.
    """
    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO scans (mdoc, timestamp, status, location)
        VALUES (?, ?, ?, ?)
    """, (mdoc, timestamp_str, status, location))
    logger.debug(f"Inserted scan: {mdoc=} {status=} {location=} {timestamp_str=}")

def get_location_name_by_prefix(prefix: str) -> Optional[str]:
    """
    Get location name by prefix (case-insensitive).

    Args:
        prefix: The location prefix.

    Returns:
        The location name or None if not found.
    """
    try:
        with sqlite3.connect(Config.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM locations WHERE UPPER(prefix) = UPPER(?)",
                (prefix.strip(),)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch location for prefix '{prefix}': {e}")
        return None

def _format_return_message(message: str, resident_not_found: bool) -> str:
    """
    Append resident warning to message if needed.

    Args:
        message: The message to format.
        resident_not_found: Whether the resident was not found.

    Returns:
        The final message.
    """
    return f"{message} Resident not found, but scan recorded." if resident_not_found else message