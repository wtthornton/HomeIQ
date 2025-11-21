"""
Simple RAG Seeding Script - Direct SQLite Access
Seeds from patterns only (doesn't require OpenVINO or full environment)
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Database path
db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_knowledge'")
if not cursor.fetchone():
    print("❌ Table 'semantic_knowledge' does not exist")
    print("   Run: python scripts/create_rag_table.py")
    conn.close()
    sys.exit(1)

# Check for existing entries
cursor.execute("SELECT COUNT(*) FROM semantic_knowledge")
existing_count = cursor.fetchone()[0]

if existing_count > 0:
    print(f"⚠️  Knowledge base already has {existing_count} entries")
    response = input("Continue seeding? (y/n): ")
    if response.lower() != "y":
        conn.close()
        sys.exit(0)

# Try to import patterns
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.patterns.common_patterns import PATTERNS

    print(f"\n📚 Seeding from {len(PATTERNS)} common patterns...")

    count = 0
    for pattern_id, pattern in PATTERNS.items():
        try:
            # Create descriptive text from pattern
            pattern_text = f"{pattern.name}. {pattern.description}. Keywords: {', '.join(pattern.keywords)}"

            # Create a simple embedding placeholder (will be replaced when real embeddings are generated)
            # For now, we'll store a placeholder that indicates this needs embedding
            embedding_placeholder = json.dumps([0.0] * 384)  # 384-dim zero vector placeholder

            # Store pattern
            cursor.execute("""
                INSERT INTO semantic_knowledge
                (text, embedding, knowledge_type, knowledge_metadata, success_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_text,
                embedding_placeholder,
                "pattern",
                json.dumps({
                    "pattern_id": pattern_id,
                    "category": pattern.category,
                    "keywords": pattern.keywords,
                    "priority": pattern.priority,
                }),
                0.9,  # Patterns are high-quality, hand-crafted
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            ))
            count += 1

            if count % 10 == 0:
                print(f"  Processed {count} patterns...")

        except Exception as e:
            print(f"⚠️  Failed to seed pattern {pattern_id}: {e}")
            continue

    conn.commit()
    print(f"✅ Seeded {count} patterns")

except ImportError as e:
    print(f"⚠️  Could not import patterns: {e}")
    print("   Patterns will be seeded when full seeding script runs with OpenVINO service")
except Exception as e:
    print(f"❌ Error seeding patterns: {e}")

# Show final count
cursor.execute("SELECT COUNT(*) FROM semantic_knowledge")
final_count = cursor.fetchone()[0]
print(f"\n📊 Total entries in knowledge base: {final_count}")

conn.close()
print("\n✅ Seeding complete!")
print("\n⚠️  Note: Embeddings are placeholders. Run full seeding script with OpenVINO service")
print("   to generate real embeddings: python scripts/seed_rag_knowledge_base.py")

