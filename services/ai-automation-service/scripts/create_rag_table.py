"""
Create semantic_knowledge table directly using SQLite
This creates the table with the final schema (knowledge_metadata column)
"""

import sqlite3
import sys
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Database path
db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    print("   Creating database directory...")
    db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check if table already exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_knowledge'")
if cursor.fetchone():
    print("✅ Table 'semantic_knowledge' already exists")
    conn.close()
    sys.exit(0)

print("Creating semantic_knowledge table...")

# Create table with final schema (knowledge_metadata, not metadata)
cursor.execute("""
    CREATE TABLE semantic_knowledge (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        embedding TEXT NOT NULL,
        knowledge_type VARCHAR NOT NULL,
        knowledge_metadata TEXT,
        success_score FLOAT NOT NULL DEFAULT 0.5,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create indexes
print("Creating indexes...")
cursor.execute("CREATE INDEX idx_knowledge_type ON semantic_knowledge (knowledge_type)")
cursor.execute("CREATE INDEX idx_success_score ON semantic_knowledge (success_score)")
cursor.execute("CREATE INDEX idx_created_at ON semantic_knowledge (created_at)")

conn.commit()

# Verify table creation
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_knowledge'")
if cursor.fetchone():
    print("✅ Table 'semantic_knowledge' created successfully")
    print("✅ Indexes created successfully")
else:
    print("❌ Failed to create table")
    conn.close()
    sys.exit(1)

# Show table structure
cursor.execute("PRAGMA table_info(semantic_knowledge)")
columns = cursor.fetchall()
print("\nTable structure:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\n✅ RAG table creation complete!")

