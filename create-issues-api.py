#!/usr/bin/env python3
"""
Create GitHub issues from markdown templates using GitHub REST API
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # Set this as environment variable
REPO_OWNER = 'wtthornton'
REPO_NAME = 'HomeIQ'
ISSUES_DIR = Path('.github-issues')

def create_issue(title, body, token):
    """Create a GitHub issue using REST API"""
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues'

    data = {
        'title': title,
        'body': body,
        'labels': ['critical', 'code-review']
    }

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('html_url')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"Error creating issue: {e.code} - {error_body}")
        return None

def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        print("\nTo set your token:")
        print("  export GITHUB_TOKEN='your_github_personal_access_token'")
        print("\nTo create a token:")
        print("  1. Go to https://github.com/settings/tokens")
        print("  2. Click 'Generate new token (classic)'")
        print("  3. Select scope: 'repo' (Full control of private repositories)")
        print("  4. Generate and copy the token")
        return 1

    issue_files = sorted(ISSUES_DIR.glob('*.md'))
    issue_files = [f for f in issue_files if f.name != 'README.md']

    if not issue_files:
        print(f"No issue files found in {ISSUES_DIR}")
        return 1

    print(f"Found {len(issue_files)} issue templates")
    print("=" * 60)

    created = 0
    failed = 0

    for issue_file in issue_files:
        with open(issue_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title (first line starting with #)
        lines = content.split('\n')
        title = lines[0].lstrip('#').strip()
        body = '\n'.join(lines[1:]).strip()

        print(f"\nCreating: {title}")

        url = create_issue(title, body, GITHUB_TOKEN)

        if url:
            print(f"  ✓ Created: {url}")
            created += 1
        else:
            print(f"  ✗ Failed to create issue")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Summary: {created} created, {failed} failed")

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    exit(main())
