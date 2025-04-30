import sys
import os
import logging
import sqlite3
from werkzeug.security import generate_password_hash

# Project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from rezscan_app.config import Config
except ImportError as e:
    print("Error: Could not import Config. Ensure you are running this from the correct project directory.")
    raise e

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    db_path = Config.DB_PATH
    logger.info(f"Database path set to: {db_path}")

    default_users = [
        {"username": "admin", "password": "admin123", "role": "admin"},
        {"username": "scheduling", "password": "schedule123", "role": "scheduling"},
        {"username": "officer", "password": "officer123", "role": "officer"},
        {"username": "viewer", "password": "viewer123", "role": "viewer"},
    ]

    conn = None
    c = None

    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()

            # Check if the users table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            if not c.fetchone():
                logger.error("Users table does not exist. Please run the application once to initialize the database.")
                raise Exception("Users table missing.")

            # Insert default users
            for user in default_users:
                username = user["username"]
                password = user["password"]
                role = user["role"]
                hashed_pw = generate_password_hash(password)

                c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
                if not c.fetchone():
                    print(f"Creating user: {username} with role: {role}")
                    c.execute(
                        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        (username, hashed_pw, role)
                    )
                    logger.info(f"User '{username}' created successfully with role '{role}'.")
                else:
                    print(f"User '{username}' already exists, skipping.")
                    logger.warning(f"User '{username}' already exists, skipping.")

            conn.commit()
            print("Default users creation process completed.")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()

