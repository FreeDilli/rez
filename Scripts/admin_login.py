import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import sqlite3
from werkzeug.security import generate_password_hash
from rezscan_app.config import Config

logger = logging.getLogger(__name__)

# Step 1: Use database path from Config
db_path = Config.DB_PATH
logger.info(f"Database path set to: {db_path}")

# Step 2: Insert sample admin user
username = 'admin'
password = 'admin123'
hashed_pw = generate_password_hash(password)
logger.info("Generated password hash for admin user")

try:
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
    logger.info("Admin user created successfully.")
except sqlite3.IntegrityError:
    logger.warning("Admin user already exists in the database.")
except sqlite3.Error as e:
    logger.error(f"Failed to insert admin user: {e}")
    raise
finally:
    c.close()
    conn.close()
