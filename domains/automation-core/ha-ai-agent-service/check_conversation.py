"""Check conversation in database"""
import sqlite3
import sys

search_id = sys.argv[1] if len(sys.argv) > 1 else "753229c4-38db-47e5-be6e-337fd33cf467"

conn = sqlite3.connect('/app/data/ha_ai_agent.db')
cursor = conn.cursor()

# Try as conversation_id
cursor.execute("SELECT conversation_id, debug_id, created_at, message_count FROM conversations WHERE conversation_id = ?", (search_id,))
result = cursor.fetchone()

if result:
    print(f"✅ Found as conversation_id:")
    print(f"  conversation_id: {result[0]}")
    print(f"  debug_id: {result[1]}")
    print(f"  created_at: {result[2]}")
    print(f"  message_count: {result[3]}")
    sys.exit(0)

# Try as debug_id
cursor.execute("SELECT conversation_id, debug_id, created_at, message_count FROM conversations WHERE debug_id = ?", (search_id,))
result = cursor.fetchone()

if result:
    print(f"✅ Found as debug_id:")
    print(f"  conversation_id: {result[0]}")
    print(f"  debug_id: {result[1]}")
    print(f"  created_at: {result[2]}")
    print(f"  message_count: {result[3]}")
    sys.exit(0)

# Try partial match
cursor.execute("SELECT conversation_id, debug_id, created_at FROM conversations WHERE conversation_id LIKE ? OR debug_id LIKE ?", (f"%{search_id[:8]}%", f"%{search_id[:8]}%"))
results = cursor.fetchall()

if results:
    print(f"Found {len(results)} conversations with partial match:")
    for r in results:
        print(f"  conversation_id: {r[0]}, debug_id: {r[1]}, created: {r[2]}")
else:
    print(f"❌ No conversation found with ID: {search_id}")
    
    # Show recent conversations
    cursor.execute("SELECT conversation_id, debug_id, created_at FROM conversations ORDER BY created_at DESC LIMIT 5")
    recent = cursor.fetchall()
    if recent:
        print(f"\nRecent conversations:")
        for r in recent:
            print(f"  conversation_id: {r[0]}")
            print(f"  debug_id: {r[1]}")
            print(f"  created_at: {r[2]}\n")

conn.close()

