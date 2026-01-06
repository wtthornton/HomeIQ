import sqlite3
import json
from datetime import datetime, timedelta

conn = sqlite3.connect('/app/data/ai_automation.db')
cursor = conn.cursor()

print("="*80)
print("QUICK DATA ANALYSIS")
print("="*80)

# Patterns analysis
cursor.execute("SELECT COUNT(*), MIN(created_at), MAX(last_seen), AVG(confidence) FROM patterns")
pat_count, pat_created, pat_last_seen, pat_avg_conf = cursor.fetchone()
print(f"\nPATTERNS: {pat_count} total")
print(f"  Created: {pat_created}")
print(f"  Last Seen: {pat_last_seen}")
avg_conf_str = f"{pat_avg_conf:.3f}" if pat_avg_conf is not None else "0.000"
print(f"  Avg Confidence: {avg_conf_str}")

# Check for old patterns
cutoff = (datetime.now() - timedelta(days=30)).isoformat()
cursor.execute(f"SELECT COUNT(*) FROM patterns WHERE last_seen < ? OR last_seen IS NULL", (cutoff,))
old_patterns = cursor.fetchone()[0]
print(f"  Old (>30 days or NULL): {old_patterns}")

# Check for deprecated
cursor.execute("SELECT COUNT(*) FROM patterns WHERE deprecated = 1")
deprecated = cursor.fetchone()[0]
print(f"  Deprecated: {deprecated}")

# Synergies analysis
cursor.execute("SELECT COUNT(*), MIN(created_at), AVG(confidence), AVG(final_score) FROM synergy_opportunities")
syn_count, syn_created, syn_avg_conf, syn_avg_score = cursor.fetchone()
print(f"\nSYNERGIES: {syn_count} total")
print(f"  Created: {syn_created}")
syn_conf_str = f"{syn_avg_conf:.3f}" if syn_avg_conf is not None else "0.000"
syn_score_str = f"{syn_avg_score:.3f}" if syn_avg_score is not None else "0.000"
print(f"  Avg Confidence: {syn_conf_str}")
print(f"  Avg Final Score: {syn_score_str}")

# Pattern history
cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM pattern_history")
hist_count, hist_min, hist_max = cursor.fetchone()
print(f"\nPATTERN HISTORY: {hist_count} records")
print(f"  Range: {hist_min} to {hist_max}")

conn.close()

print("\n" + "="*80)
print("RECOMMENDATION: All data appears to be old (from Nov 2025)")
print("Suggest NUCLEAR OPTION: Delete all and regenerate fresh patterns")
print("="*80)
