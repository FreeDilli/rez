# admin_login.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

# Step 1: Match the real database location (same as app)
script_dir = os.path.dirname(os.path.abspath(__file__))  # /RezScan App
db_path = os.path.join(script_dir, 'rezscan.db')         # /RezScan App/rezscan.db

# Step 2: Create users table if needed
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin', 'viewer')) NOT NULL
    )
''')

conn.commit()
print("✅ Users table created if it didn't exist.")

# Step 3: Insert sample admin
username = 'admin'
password = 'admin123'
hashed_pw = generate_password_hash(password)

try:
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
              (username, hashed_pw, 'admin'))
    conn.commit()
    print("✅ Admin user created.")
except sqlite3.IntegrityError:
    print("⚠️ User already exists.")

conn.close()
