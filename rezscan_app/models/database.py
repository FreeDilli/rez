import logging
import sqlite3
import os
from flask import g, current_app

# Configure logging
logger = logging.getLogger(__name__)

def get_db():
    if 'db' not in g:
        try:
            db_path = current_app.config['DB_PATH']
            logger.debug(f"Opening database connection to: {db_path}")
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys = ON')  # Enable foreign keys
            logger.debug("Database connection established with foreign keys enabled")
        except sqlite3.Error as e:
            logger.error(f"Error opening database connection: {str(e)}")
            raise
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
            logger.debug("Database connection closed")
        except sqlite3.Error as e:
            logger.error(f"Error closing database connection: {str(e)}")

def init_db():
    db_path = current_app.config['DB_PATH']
    logger.debug(f"Preparing to initialize database at: {db_path}")
    
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        logger.debug(f"Created database directory: {os.path.dirname(db_path)}")
    except OSError as e:
        logger.error(f"Error creating database directory: {str(e)}")
        raise

    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            logger.debug("Established temporary connection for database initialization")

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
                logger.debug("Created residents table")
            except sqlite3.Error as e:
                logger.error(f"Error creating residents table: {str(e)}")
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
                logger.debug("Created locations table")
            except sqlite3.Error as e:
                logger.error(f"Error creating locations table: {str(e)}")
                raise

            # Scans table
            try:
                c.execute('''
                    CREATE TABLE IF NOT EXISTS scans (
                        scanid INTEGER PRIMARY KEY AUTOINCREMENT,
                        mdoc TEXT NOT NULL,
                        timestamp DATETIME,
                        status TEXT,
                        location TEXT
                    )
                ''')
                logger.debug("Created scans table")
            except sqlite3.Error as e:
                logger.error(f"Error creating scans table: {str(e)}")
                raise

            # Users table
            try:
                c.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        theme TEXT,
                        default_view TEXT,
                        last_login DATETIME
                    )
                ''')
                logger.debug("Created users table")
            except sqlite3.Error as e:
                logger.error(f"Error creating users table: {str(e)}")
                raise

            # Scans view
            try:
                c.execute('''
                    CREATE VIEW IF NOT EXISTS scans_with_residents AS
                    SELECT 
                        s.mdoc,
                        r.name,
                        s.timestamp,
                        s.status,
                        s.location
                    FROM scans s
                    LEFT JOIN residents r ON s.mdoc = r.mdoc
                ''')
                logger.debug("Created scans_with_residents view")
            except sqlite3.Error as e:
                logger.error(f"Error creating scans_with_residents view: {str(e)}")
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
                logger.debug("Created audit_log table")
            except sqlite3.Error as e:
                logger.error(f"Error creating audit_log table: {str(e)}")
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
                logger.debug("Created schedule_groups table")
            except sqlite3.Error as e:
                logger.error(f"Error creating schedule_groups table: {str(e)}")
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
                logger.debug("Created schedule_blocks table")
            except sqlite3.Error as e:
                logger.error(f"Error creating schedule_blocks table: {str(e)}")
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
                logger.debug("Created resident_schedules table")
            except sqlite3.Error as e:
                logger.error(f"Error creating resident_schedules table: {str(e)}")
                raise

            # Import History table
            try:
                c.execute('''
                    CREATE TABLE IF NOT EXISTS import_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        username TEXT NOT NULL,
                        added INTEGER DEFAULT 0,
                        updated INTEGER DEFAULT 0,
                        deleted INTEGER DEFAULT 0,
                        failed INTEGER DEFAULT 0,
                        total INTEGER DEFAULT 0,
                        csv_content TEXT
                    )
                ''')
                logger.debug("Created import_history table")
            except sqlite3.Error as e:
                logger.error(f"Error creating import_history table: {str(e)}")
                raise
        
            # Resident Backups table
            try:
                c.execute('''
                    CREATE TABLE IF NOT EXISTS resident_backups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        import_id INTEGER,
                        mdoc TEXT,
                        name TEXT,
                        unit TEXT,
                        housing_unit TEXT,
                        level TEXT,
                        photo TEXT,
                        FOREIGN KEY (import_id) REFERENCES import_history(id) ON DELETE CASCADE
                    )
                ''')
                logger.debug("Created resident_backups table")
            except sqlite3.Error as e:
                logger.error(f"Error creating resident_backups table: {str(e)}")
                raise
            
            # Settings table
            try:
                c.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT,
                        UNIQUE(category, key)
                    )
                ''')
                logger.debug("Created settings table")
            except sqlite3.Error as e:
                logger.error(f"Error creating settings table: {str(e)}")
                raise
            
            # Seed default settings if none exist
            try:
                c.execute('SELECT COUNT(*) FROM settings')
                if c.fetchone()[0] == 0:
                    c.executemany('''
                        INSERT INTO settings (category, key, value) VALUES (?, ?, ?)
                        ''', [
                            ('api', 'coris_api_url', 'https://coris.example.gov/api/residents'),
                            ('api', 'coris_api_key', 'changeme-key'),
                            ('flags', 'enable_kiosk_mode', 'true'),
                            ('flags', 'training_mode', 'false'),
                            ('ui', 'default_theme', 'light')
                        ])
                logger.info("Seeded default settings")
            except sqlite3.Error as e:
                logger.error(f"Error seeding default settings: {str(e)}")
                raise
                
            # Commit changes
            conn.commit()
            logger.info("Database schema creation completed")

            # Verify tables
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall()]
            logger.info(f"Tables in database: {', '.join(tables)}")

    except sqlite3.Error as e:
        logger.error(f"Error during database initialization: {str(e)}")
        raise

def init_app(app):
    logger.debug("Registering database teardown with Flask app")
    app.teardown_appcontext(close_db)