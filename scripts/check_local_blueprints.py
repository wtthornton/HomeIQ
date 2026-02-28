"""Check blueprints in PostgreSQL database."""
import os

import psycopg2

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

conn = psycopg2.connect(POSTGRES_URL)
cursor = conn.cursor()

# Count total blueprints
cursor.execute("SELECT COUNT(*) FROM blueprints.indexed_blueprints")
total = cursor.fetchone()[0]
print(f"Database has {total} blueprints")

# Find motion-related blueprints
cursor.execute("""
    SELECT name, source_url, description
    FROM blueprints.indexed_blueprints
    WHERE name ILIKE '%%motion%%' OR description ILIKE '%%motion%%'
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
    FROM blueprints.indexed_blueprints
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
    FROM blueprints.indexed_blueprints
    ORDER BY indexed_at DESC
    LIMIT 5
""")
recent = cursor.fetchall()
print(f"\nMost recently indexed blueprints:")
for name, url, indexed_at in recent:
    print(f"  - {name}")
    print(f"    Indexed: {indexed_at}")

conn.close()
print("\n[OK] Database verification complete!")
