"""Script to find bugs in ai-automation-service-new"""
import ast
import re
from pathlib import Path

bugs = []

def check_file(filepath: Path):
    """Check a Python file for common bugs"""
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Bug 1: Operator precedence issues with 'not' and '=='
        for i, line in enumerate(lines, 1):
            if re.search(r'if\s+not\s+\w+\.get\([^)]+\)\s*==', line):
                bugs.append({
                    'file': str(filepath),
                    'line': i,
                    'type': 'operator_precedence',
                    'message': f"Operator precedence bug: 'not x == y' should be 'x != y' or 'not (x == y)'",
                    'code': line.strip()
                })
        
        # Bug 2: Default None with Depends()
        for i, line in enumerate(lines, 1):
            if 'Depends(' in line and '= None' in line:
                bugs.append({
                    'file': str(filepath),
                    'line': i,
                    'type': 'invalid_default',
                    'message': "Cannot use '= None' default with Depends() - remove default value",
                    'code': line.strip()
                })
        
        # Bug 3: Missing None check before attribute access
        for i, line in enumerate(lines, 1):
            if re.search(r'\.get\([^)]+\)\.\w+', line) and 'if' not in line[:20]:
                # Check if previous lines have None check
                context = '\n'.join(lines[max(0, i-3):i])
                if 'if' not in context.lower() or 'none' not in context.lower():
                    bugs.append({
                        'file': str(filepath),
                        'line': i,
                        'type': 'missing_none_check',
                        'message': "Potential AttributeError: .get() may return None, check before attribute access",
                        'code': line.strip()
                    })
        
        # Bug 4: Incorrect comparison with None
        for i, line in enumerate(lines, 1):
            if re.search(r'==\s+None|!=\s+None', line):
                bugs.append({
                    'file': str(filepath),
                    'line': i,
                    'type': 'none_comparison',
                    'message': "Use 'is None' or 'is not None' instead of '== None' or '!= None'",
                    'code': line.strip()
                })
        
        # Bug 5: Missing await in async context
        # This is harder to detect statically, skip for now
        
        # Bug 6: Resource leak - missing close/cleanup
        # Check for httpx.AsyncClient without context manager
        has_async_client = False
        has_close = False
        for i, line in enumerate(lines, 1):
            if 'AsyncClient(' in line:
                has_async_client = True
            if 'close()' in line or 'aclose()' in line:
                has_close = True
        if has_async_client and not has_close:
            # Check if used as context manager
            if '__aenter__' not in content and '__aexit__' not in content:
                bugs.append({
                    'file': str(filepath),
                    'line': 1,
                    'type': 'resource_leak',
                    'message': "httpx.AsyncClient should be closed or used as context manager",
                    'code': 'File-level issue'
                })
        
    except Exception as e:
        print(f"Error checking {filepath}: {e}")

# Check all Python files
src_dir = Path('src')
for py_file in src_dir.rglob('*.py'):
    check_file(py_file)

# Print results
print(f"Found {len(bugs)} potential bugs:\n")
for i, bug in enumerate(bugs[:10], 1):
    print(f"Bug #{i}:")
    print(f"  File: {bug['file']}")
    print(f"  Line: {bug['line']}")
    print(f"  Type: {bug['type']}")
    print(f"  Message: {bug['message']}")
    print(f"  Code: {bug['code']}")
    print()
