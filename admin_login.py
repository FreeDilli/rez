import logging
from Utils.logging_config import setup_logging
import sqlite3
from werkzeug.security import generate_password_hash
from config import Config
import os

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Step 1: Use database path from Config
app_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(app_dir, "rezscan.db")

# Step 2: Create users table if needed
try:
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
    logger.info("Users table created if it didn't exist.")
except sqlite3.Error as e:
    logger.error(f"Failed to create users table: {e}")
    raise
finally:
    c.close()
    conn.close()

# Step 3: Insert sample admin
username = 'admin'
password = 'admin123'
hashed_pw = generate_password_hash(password)
logger.debug("Generated password hash for admin user")

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
              (username, hashed_pw, 'admin'))
    conn.commit()
    logger.info("Admin user created successfully.")
except sqlite3.IntegrityError:
    logger.warning("Admin user already exists in the database.")
except sqlite3.Error as e:
    logger.error(f"Failed to insert admin user: {e}")
    raise
finally:
    c.close()
    conn.close()