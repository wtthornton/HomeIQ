import json

with open('review-results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

issues = []
for file_data in data.get('files', []):
    file_path = file_data.get('path', 'unknown')
    for issue in file_data.get('issues', []):
        severity = issue.get('severity', '').lower()
        issue_type = issue.get('type', '').lower()
        if severity in ['critical', 'high', 'medium'] or issue_type in ['bug', 'error', 'security']:
            issues.append((file_path, issue))

print(f'Found {len(issues)} bugs/issues\n')
for i, (path, issue) in enumerate(issues[:15], 1):
    line = issue.get('line', '?')
    message = issue.get('message', 'no message')
    severity = issue.get('severity', 'unknown')
    issue_type = issue.get('type', 'unknown')
    print(f"{i}. {path}:{line} [{severity}/{issue_type}]")
    print(f"   {message[:150]}\n")
