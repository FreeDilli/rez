# This will run the parser for auto-fill suggestions on the movement upload.

import sqlite3
import re

DB_PATH = "RezScan App/data/rezscan.db"

def parse_source_line(line):
    # Example: "User, Test - Echo"
    if not line or ',' not in line:
        return None, None

    parts = line.split('-')
    name_part = parts[0].strip()
    housing_part = parts[1].strip() if len(parts) > 1 else None

    return name_part, housing_part

def update_suggested_fields():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id, source_line, suggested_name, suggested_housing
        FROM schedule_match_review
        WHERE (suggested_name IS NULL OR suggested_name = '')
           OR (suggested_housing IS NULL OR suggested_housing = '')
    """)
    rows = cur.fetchall()

    updates = 0
    for row in rows:
        name, housing = parse_source_line(row['source_line'])

        if not name:
            continue  # Skip if we can't parse a name

        cur.execute("""
            UPDATE schedule_match_review
            SET suggested_name = ?, suggested_housing = ?
            WHERE id = ?
        """, (name, housing, row['id']))
        updates += 1

    conn.commit()
    conn.close()
    print(f"✅ Updated {updates} record(s) based on source_line.")

if __name__ == "__main__":
    update_suggested_fields()
