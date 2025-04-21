import sqlite3
import os
from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(os.getenv('DB_PATH', 'rezscan.db'))
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with sqlite3.connect(os.getenv('DB_PATH', 'rezscan.db')) as conn:
        c = conn.cursor()
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                prefix TEXT UNIQUE,
                type TEXT 
            )
        ''')
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