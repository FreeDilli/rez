import sqlite3
from werkzeug.security import generate_password_hash

# Paths
DB_PATH = 'data/rezscan.db'  # Adjust if your database is in a different location

# Users and new passwords
reset_users = {
    'admin': 'admin123',
    'viewer': 'viewer123',
    'officer': 'officer123'
}

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for username, plain_password in reset_users.items():
        hashed_password = generate_password_hash(plain_password)
        c.execute("""
            UPDATE users
            SET password = ?
            WHERE username = ?
        """, (hashed_password, username))

    conn.commit()
    print("✅ Passwords reset successfully!")

except sqlite3.Error as e:
    print(f"❌ Database error: {e}")

finally:
    if conn:
        conn.close()

