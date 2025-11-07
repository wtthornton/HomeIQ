import sqlite3
from pathlib import Path

db_path = Path("services/ai-automation-service/data/ai_automation.db")
if not db_path.exists():
    db_path = Path("data/ai_automation.db")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables in {db_path}:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} rows")
    conn.close()
else:
    print(f"Database not found at {db_path}")

