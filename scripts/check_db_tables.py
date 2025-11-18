import sqlite3

conn = sqlite3.connect('data/ai_automation.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables in database:")
for table in tables:
    print(f"  - {table}")
    
# Check if ask_ai_queries exists with different case
if 'ask_ai_queries' not in tables:
    print("\nChecking for similar table names...")
    for table in tables:
        if 'ask' in table.lower() or 'query' in table.lower() or 'suggestion' in table.lower():
            print(f"  Found: {table}")

conn.close()
