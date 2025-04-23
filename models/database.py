import logging
import sqlite3
import os
from flask import g, current_app
from Utils.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

def get_db():
    if 'db' not in g:
        db_path = current_app.config['DB_PATH']
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')  # Enable foreign keys
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db_path = current_app.config['DB_PATH']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    logger.info(f"Initializing database at: {db_path}")

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()

        # Residents table
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS residents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    mdoc TEXT UNIQUE NOT NULL,
                    unit TEXT,
                    housing_unit TEXT,
                    level TEXT,
                    photo TEXT
                )
            ''')
            logger.info("Created residents table")
        except sqlite3.Error as e:
            logger.error(f"Error creating residents table: {e}")
            raise

        # Locations table
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    prefix TEXT UNIQUE,
                    type TEXT
                )
            ''')
            logger.info("Created locations table")
        except sqlite3.Error as e:
            logger.error(f"Error creating locations table: {e}")
            raise

        # Scans table
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS scans (
                    scanid INTEGER PRIMARY KEY AUTOINCREMENT,
                    mdoc TEXT,
                    date DATE,
                    time TIME,
                    status TEXT,
                    location TEXT
                )
            ''')
            logger.info("Created scans table")
        except sqlite3.Error as e:
            logger.error(f"Error creating scans table: {e}")
            raise

        # Users table
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT CHECK(role IN ('admin', 'viewer')) NOT NULL,
                    last_login DATETIME
                )
            ''')
            logger.info("Created users table")
        except sqlite3.Error as e:
            logger.error(f"Error creating users table: {e}")
            raise

        # Scans view
        try:
            c.execute('''
                CREATE VIEW IF NOT EXISTS scans_with_residents AS
                SELECT 
                    s.mdoc,
                    r.name,
                    s.date,
                    s.time,
                    s.status,
                    s.location
                FROM scans s
                LEFT JOIN residents r ON s.mdoc = r.mdoc
            ''')
            logger.info("Created scans_with_residents view")
        except sqlite3.Error as e:
            logger.error(f"Error creating scans_with_residents view: {e}")
            raise

        # Audit Log table
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            logger.info("Created audit_log table")
        except sqlite3.Error as e:
            logger.error(f"Error creating audit_log table: {e}")
            raise

        # Schedule Groups table
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS schedule_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL
                )
            ''')
            logger.info("Created schedule_groups table")
        except sqlite3.Error as e:
            logger.error(f"Error creating schedule_groups table: {e}")
            raise

        # Schedule Blocks table
        try:
            c.execute('''
            CREATE TABLE IF NOT EXISTS schedule_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                day_of_week TEXT NOT NULL,
                location TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                week_type TEXT DEFAULT 'both',
                FOREIGN KEY (group_id) REFERENCES schedule_groups(id) ON DELETE CASCADE
                )
            ''')
            logger.info("Created schedule_blocks table")
        except sqlite3.Error as e:
            logger.error(f"Error creating schedule_blocks table: {e}")
            raise

        # Resident Schedule Assignments table
        try:
            c.execute('''
            CREATE TABLE IF NOT EXISTS resident_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mdoc TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                FOREIGN KEY (group_id) REFERENCES schedule_groups(id) ON DELETE CASCADE
    )
            ''')
            logger.info("Created resident_schedules table")
        except sqlite3.Error as e:
            logger.error(f"Error creating resident_schedules table: {e}")
            raise

        # Commit changes
        conn.commit()
        logger.info("Database initialized successfully")

        # Verify tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        logger.info(f"Tables in database: {tables}")

def init_app(app):
    app.teardown_appcontext(close_db)