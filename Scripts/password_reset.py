import sqlite3
from werkzeug.security import generate_password_hash

# Set your database path
DB_PATH = "data/rezscan.db"

# Set username and new password
USERNAME_TO_RESET = "admin"
NEW_PASSWORD = "admin123"

# Generate the correct hash
new_password_hash = generate_password_hash(NEW_PASSWORD, method='scrypt')
print(f"Generated password hash: {new_password_hash}")

# Connect to the database and update
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check if user exists
c.execute("SELECT id FROM users WHERE username = ?", (USERNAME_TO_RESET,))
user = c.fetchone()

if user:
    c.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (new_password_hash, USERNAME_TO_RESET)
    )
    conn.commit()
    print(f"[+] Successfully updated password for user: {USERNAME_TO_RESET}")
else:
    print(f"[!] User {USERNAME_TO_RESET} not found.")

conn.close()
# Scripts/password_reset.py
import sqlite3
from werkzeug.security import generate_password_hash
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'rezscan_app', 'data', 'rezscan.db')

# Define users and their new passwords
users_to_reset = {
    'admin': {
        'password': 'admin123',
        'role': 'admin'
    },
    'viewer': {
        'password': 'viewer123',
        'role': 'viewer'
    },
    'officer': {
        'password': 'officer123',
        'role': 'officer'
    },
    'scheduling': {
        'password': 'scheduling123',
        'role': 'scheduling'
    }
}

def reset_passwords():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for username, info in users_to_reset.items():
        hashed_password = generate_password_hash(info['password'], method="scrypt")
        
        try:
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            user = c.fetchone()

            if user:
                c.execute("UPDATE users SET password = ?, role = ? WHERE username = ?", (hashed_password, info['role'], username))
                print(f"[+] Updated existing user '{username}'")
            else:
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, info['role']))
                print(f"[+] Created new user '{username}'")

        except sqlite3.Error as e:
            print(f"[!] Error processing {username}: {e}")

    conn.commit()
    conn.close()
    print("\n[✓] Password reset process completed successfully.")

if __name__ == '__main__':
    reset_passwords()
