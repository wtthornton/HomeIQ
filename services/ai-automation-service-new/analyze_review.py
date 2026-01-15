import json
import sys

with open('review-results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_issues = []
for file_result in data.get('files', []):
    for issue in file_result.get('issues', []):
        issue['file'] = file_result.get('file', '')
        all_issues.append(issue)

# Filter for bugs and critical issues
bugs = []
for issue in all_issues:
    severity = issue.get('severity', '').lower()
    issue_type = issue.get('type', '').lower()
    message = issue.get('message', '').lower()
    
    # Look for actual bugs: errors, exceptions, logic errors, etc.
    if (severity in ['error', 'critical'] or 
        'bug' in issue_type or 
        'exception' in message or 
        'error' in message or
        'undefined' in message or
        'missing' in message and 'import' in message or
        'unused' in message and 'variable' in message or
        'undefined' in message):
        bugs.append(issue)

print(f"Found {len(bugs)} potential bugs/issues\n")
print("=" * 80)

# Show top bugs
for i, bug in enumerate(bugs[:10], 1):
    print(f"\nBug #{i}:")
    print(f"  Type: {bug.get('type', 'unknown')}")
    print(f"  Severity: {bug.get('severity', 'unknown')}")
    print(f"  File: {bug.get('file', 'unknown')}")
    print(f"  Line: {bug.get('line', 'unknown')}")
    print(f"  Message: {bug.get('message', '')[:200]}")

# Save top 5 bugs to a separate file for fixing
top_bugs = bugs[:5]
with open('top_bugs.json', 'w', encoding='utf-8') as f:
    json.dump(top_bugs, f, indent=2)

print(f"\n\nTop 5 bugs saved to top_bugs.json")
