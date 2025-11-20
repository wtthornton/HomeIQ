"""
Simple RAG Statistics Query - Direct SQLite Access
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Database path
db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_knowledge'")
if not cursor.fetchone():
    print("\n⚠️  RAG Knowledge Base table does not exist")
    print("   Run migration: alembic upgrade head")
    conn.close()
    exit(0)

# Total count
cursor.execute("SELECT COUNT(*) as total FROM semantic_knowledge")
total = cursor.fetchone()['total']

if total == 0:
    print("\n⚠️  RAG Knowledge Base is EMPTY")
    print("   Run: python scripts/seed_rag_knowledge_base.py")
    conn.close()
    exit(0)

# Count by type
cursor.execute("""
    SELECT knowledge_type, COUNT(*) as count 
    FROM semantic_knowledge 
    GROUP BY knowledge_type
    ORDER BY count DESC
""")
type_counts = cursor.fetchall()

# Most recent update
cursor.execute("""
    SELECT updated_at, knowledge_type, text, success_score
    FROM semantic_knowledge
    ORDER BY updated_at DESC
    LIMIT 1
""")
most_recent = cursor.fetchone()

# Oldest entry
cursor.execute("""
    SELECT created_at, knowledge_type, text, success_score
    FROM semantic_knowledge
    ORDER BY created_at ASC
    LIMIT 1
""")
oldest = cursor.fetchone()

# Average success score
cursor.execute("SELECT AVG(success_score) as avg_score FROM semantic_knowledge")
avg_score = cursor.fetchone()['avg_score']

# Recent entries (last 5)
cursor.execute("""
    SELECT updated_at, knowledge_type, substr(text, 1, 60) as text_preview, success_score
    FROM semantic_knowledge
    ORDER BY updated_at DESC
    LIMIT 5
""")
recent_entries = cursor.fetchall()

# Print statistics
print("\n" + "="*70)
print("RAG KNOWLEDGE BASE STATISTICS")
print("="*70)

print(f"\n📊 Total Entries: {total}")

print("\n📚 Entries by Type:")
for row in type_counts:
    percentage = (row['count'] / total) * 100
    print(f"   - {row['knowledge_type']:20s}: {row['count']:4d} ({percentage:5.1f}%)")

print("\n📈 Success Score:")
print(f"   - Average: {avg_score:.3f}")

if most_recent:
    print("\n🕐 Most Recent Update:")
    print(f"   - Date: {most_recent['updated_at']}")
    print(f"   - Type: {most_recent['knowledge_type']}")
    print(f"   - Text: {most_recent['text'][:80]}...")
    print(f"   - Success Score: {most_recent['success_score']:.3f}")

if oldest:
    print("\n📅 Oldest Entry:")
    print(f"   - Date: {oldest['created_at']}")
    print(f"   - Type: {oldest['knowledge_type']}")
    print(f"   - Text: {oldest['text'][:80]}...")
    print(f"   - Success Score: {oldest['success_score']:.3f}")

# Age calculation
if oldest and most_recent:
    try:
        oldest_date = datetime.fromisoformat(oldest['created_at'].replace('Z', '+00:00'))
        recent_date = datetime.fromisoformat(most_recent['updated_at'].replace('Z', '+00:00'))
        age_days = (recent_date - oldest_date).days
        print("\n⏱️  Knowledge Base Age:")
        print(f"   - {age_days} days between oldest and most recent")
    except:
        pass

print("\n📝 Recent Entries (Last 5):")
for i, entry in enumerate(recent_entries, 1):
    print(f"   {i}. [{entry['knowledge_type']}] {entry['updated_at']}")
    print(f"      {entry['text_preview']}...")

print("\n" + "="*70)

conn.close()

