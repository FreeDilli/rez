import logging
from Utils.logging_config import setup_logging
import sqlite3
from werkzeug.security import generate_password_hash
from config import Config
import os

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# ✅ Use DB_PATH from config
db_path = Config.DB_PATH
logger.info(f"📂 Using DB path: {db_path}")

# Make sure the directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Step 1: Create users table
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
    logger.info("✅ Users table created (if not exists).")
except sqlite3.Error as e:
    logger.error(f"❌ Failed to create users table: {e}")
    raise
finally:
    if 'c' in locals(): c.close()
    if 'conn' in locals(): conn.close()

# Step 2: Insert admin user
username = 'admin'
password = 'admin123'
hashed_pw = generate_password_hash(password)
logger.debug("🔐 Password hashed for admin.")

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
              (username, hashed_pw, 'admin'))
    conn.commit()
    logger.info("✅ Admin user created.")
except sqlite3.IntegrityError:
    logger.warning("⚠️ Admin user already exists.")
except sqlite3.Error as e:
    logger.error(f"❌ Failed to insert admin user: {e}")
    raise
finally:
    if 'c' in locals(): c.close()
    if 'conn' in locals(): conn.close()
