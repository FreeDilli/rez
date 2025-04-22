import sqlite3
import os
from flask import g, current_app
from config import Config

def get_db():
    if 'db' not in g:
        db_path = current_app.config['DB_PATH']
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    # Explicitly place DB in the correct folder
    app_root = os.path.dirname(os.path.abspath(__file__))  # This gives you /RezScan App/models
    parent_dir = os.path.abspath(os.path.join(app_root, '..'))  # Go up to /RezScan App
    db_path = os.path.join(parent_dir, 'rezscan.db')  # Final path: /RezScan App/rezscan.db

    print(f"🔨 Initializing DB at: {db_path}")

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()

        # Residents table
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

        # Locations table
        c.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                prefix TEXT UNIQUE,
                type TEXT 
            )
        ''')

        # Scans table
        c.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                scanid INTEGER PRIMARY KEY AUTOINCREMENT,
                mdoc TEXT,
                date TEXT,
                time TEXT,
                status TEXT,
                location TEXT
            )
        ''')

        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT CHECK(role IN ('admin', 'viewer')) NOT NULL
            )
        ''')

        # View for Scan Log with resident names
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

        conn.commit()
        

def init_app(app):
    app.teardown_appcontext(close_db)
