import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union
from config import Config
from Utils.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

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
        # Validate inputs
        if not mdoc or not prefix:
            logger.warning(f"Invalid input: mdoc='{mdoc}', prefix='{prefix}'")
            return "Invalid input: MDOC and prefix cannot be empty."

        location_name = get_location_name_by_prefix(prefix)
        if not location_name:
            logger.warning(f"Prefix '{prefix}' not found")
            return f"Prefix '{prefix}' not associated with any location."

        with sqlite3.connect(Config.DB_PATH) as conn:
            cursor = conn.cursor()

            # Check resident existence
            cursor.execute("SELECT id FROM residents WHERE mdoc = ?", (mdoc,))
            resident = cursor.fetchone()
            resident_not_found = not resident
            if resident_not_found:
                logger.warning(f"Resident with MDOC '{mdoc}' not found, but scan will be recorded")

            # Check last scan
            cursor.execute("""
                SELECT location, status, date || ' ' || time AS timestamp
                FROM scans
                WHERE mdoc = ?
                ORDER BY datetime(timestamp) DESC
                LIMIT 1
            """, (mdoc,))
            last_scan = cursor.fetchone()

            now = datetime.now()
            scan_time = now
            out_time = now - timedelta(seconds=1)  # 1 second earlier for Out scan

            if last_scan:
                last_location, last_status, _ = last_scan

                if last_status == 'In' and last_location != location_name:
                    # Missed scan: insert 'Out' for last location, 'In' for new
                    insert_scan(cursor, mdoc, out_time, 'Out', last_location)
                    insert_scan(cursor, mdoc, scan_time, 'In', location_name)
                    conn.commit()
                    message = (
                        f"Scan recorded: 'Out' at {last_location}, 'In' at {location_name}. "
                        f"(Missed scan corrected)"
                    )
                    logger.info(f"Processed missed scan for MDOC '{mdoc}': Out at {last_location}, In at {location_name}")
                    return _format_return_message(message, resident_not_found)

                if last_location == location_name:
                    # Same location: toggle status
                    status = 'Out' if last_status == 'In' else 'In'
                    insert_scan(cursor, mdoc, scan_time, status, location_name)
                    conn.commit()
                    message = f"Scan recorded: '{status}' at {location_name}"
                    logger.info(f"Processed scan for MDOC '{mdoc}': {status} at {location_name}")
                    return _format_return_message(message, resident_not_found)

            # Default: new 'In' scan
            insert_scan(cursor, mdoc, scan_time, 'In', location_name)
            conn.commit()
            message = f"Scan recorded: 'In' at {location_name}"
            logger.info(f"Processed scan for MDOC '{mdoc}': In at {location_name}")
            return _format_return_message(message, resident_not_found)

    except sqlite3.Error as e:
        logger.error(f"Failed to process scan for MDOC '{mdoc}' at prefix '{prefix}': {e}")
        return f"Database error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error processing scan for MDOC '{mdoc}' at prefix '{prefix}': {e}")
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
    date_str = timestamp.strftime('%Y-%m-%d')
    time_str = timestamp.strftime('%H:%M:%S')
    cursor.execute("""
        INSERT INTO scans (mdoc, date, time, status, location)
        VALUES (?, ?, ?, ?, ?)
    """, (mdoc, date_str, time_str, status, location))
    logger.debug(f"Inserted scan: MDOC='{mdoc}', status='{status}', location='{location}', time='{date_str} {time_str}'")

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
        logger.error(f"Failed to query location for prefix '{prefix}': {e}")
        return None

def _format_return_message(message: str, resident_not_found: bool) -> str:
    """
    Format the return message, appending resident not found info if applicable.
    
    Args:
        message: The base message.
        resident_not_found: Whether the resident was not found.
    
    Returns:
        The formatted message.
    """
    if resident_not_found:
        return f"{message} Resident not found, but scan recorded."
    return message