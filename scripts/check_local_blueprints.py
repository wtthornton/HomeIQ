"""Check blueprints in local database."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "blueprint_index.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Count total blueprints
cursor.execute("SELECT COUNT(*) FROM indexed_blueprints")
total = cursor.fetchone()[0]
print(f"Local database has {total} blueprints")

# Find motion-related blueprints
cursor.execute("""
    SELECT name, source_url, description 
    FROM indexed_blueprints 
    WHERE name LIKE '%motion%' OR name LIKE '%Motion%' OR description LIKE '%motion%'
    LIMIT 10
""")
results = cursor.fetchall()
print(f"\nBlueprints with 'motion' in name or description: {len(results)}")
for name, url, desc in results:
    print(f"  - {name}")
    if desc:
        print(f"    Description: {desc[:80]}...")
    print(f"    URL: {url}")

# Test search by domain
cursor.execute("""
    SELECT name, domain, required_domains 
    FROM indexed_blueprints 
    WHERE required_domains IS NOT NULL
    LIMIT 5
""")
domain_results = cursor.fetchall()
print(f"\nBlueprints with domain requirements: {len(domain_results)}")
for name, domain, req_domains in domain_results:
    print(f"  - {name} (domain: {domain})")
    if req_domains:
        print(f"    Required domains: {req_domains}")

# Show recent imports
cursor.execute("""
    SELECT name, source_url, indexed_at 
    FROM indexed_blueprints 
    ORDER BY indexed_at DESC 
    LIMIT 5
""")
recent = cursor.fetchall()
print(f"\nMost recently indexed blueprints:")
for name, url, indexed_at in recent:
    print(f"  - {name}")
    print(f"    Indexed: {indexed_at}")

conn.close()
print("\n[OK] Local database verification complete!")
print("\nNOTE: Docker service uses a separate database volume.")
print("To sync: Update docker-compose.yml to mount ./data:/app/data")
