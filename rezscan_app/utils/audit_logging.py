import logging
import sqlite3
from rezscan_app.models.database import get_db

logger = logging.getLogger(__name__)

def log_audit_action(username, action, target, details=None):
    """Log an action to the audit_log table and logger."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO audit_log (username, action, target, details) VALUES (?, ?, ?, ?)",
                (username, action, target, details)
            )
            conn.commit()
            logger.debug(f"Audit log created: {username} - {action} - {target}")
    except sqlite3.Error as e:
        logger.error(f"Failed to log audit action for {username}: {str(e)}")