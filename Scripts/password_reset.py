import sys
import os
import logging
import sqlite3
from werkzeug.security import generate_password_hash

# --- Configure Logging ---
logger = logging.getLogger(__name__)

# --- Set database path manually (no relying on Config) ---
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.abspath(os.path.join(base_dir, '..', 'data', 'rezscan.db'))

print(f"Using database at: {db_path}")
logger.info(f"Database path set to: {db_path}")

# --- Insert sample admin user ---
username = 'admin'
password = 'admin123'
hashed_pw = generate_password_hash(password)
logger.info("Generated password hash for admin user.")

try:
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist at {db_path}")
        raise FileNotFoundError(f"Database file not found: {db_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check if the users table exists first
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if not c.fetchone():
        logger.error("Users table does not exist. Please run the application once to initialize the database.")
        raise Exception("Users table missing.")

    # Try to insert admin user
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
              (username, hashed_pw, 'admin'))
    conn.commit()
    logger.info("✅ Admin user created successfully.")

except sqlite3.IntegrityError:
    logger.warning("⚠️ Admin user already exists in the database.")
except Exception as e:
    logger.error(f"❌ Failed to insert admin user: {str(e)}")
    raise
finally:
    if 'c' in locals():
        c.close()
    if 'conn' in locals():
        conn.close()

