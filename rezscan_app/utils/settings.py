def is_training_mode():
    from rezscan_app.models.database import get_db
    try:
        with get_db() as db:
            c = db.cursor()
            c.execute("SELECT value FROM settings WHERE category = 'flags' AND key = 'training_mode'")
            row = c.fetchone()
            return row and row[0].strip().lower() == 'true'
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to check training mode: {e}")
        return False
