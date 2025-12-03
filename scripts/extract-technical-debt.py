#!/usr/bin/env python3
"""
Extract and categorize TODO/FIXME comments from codebase.
Creates a prioritized technical debt backlog.
"""

import re
import os
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Patterns to match TODO/FIXME comments
TODO_PATTERNS = [
    r'TODO[:\s]+(.+?)(?:\n|$)',
    r'FIXME[:\s]+(.+?)(?:\n|$)',
    r'XXX[:\s]+(.+?)(?:\n|$)',
    r'HACK[:\s]+(.+?)(?:\n|$)',
    r'NOTE[:\s]+(.+?)(?:\n|$)',  # Sometimes used for technical debt
]

# Priority keywords
PRIORITY_KEYWORDS = {
    'critical': ['critical', 'security', 'vulnerability', 'bug', 'crash', 'data loss', 'leak'],
    'high': ['high', 'important', 'production', 'performance', 'error', 'fail'],
    'medium': ['medium', 'improve', 'enhance', 'refactor', 'optimize'],
    'low': ['low', 'nice', 'future', 'maybe', 'consider'],
}

# Category keywords
CATEGORY_KEYWORDS = {
    'security': ['security', 'auth', 'authentication', 'authorization', 'vulnerability', 'injection', 'xss', 'csrf'],
    'performance': ['performance', 'slow', 'latency', 'optimize', 'cache', 'query'],
    'testing': ['test', 'testing', 'coverage', 'mock', 'fixture'],
    'documentation': ['doc', 'documentation', 'comment', 'explain'],
    'refactoring': ['refactor', 'cleanup', 'simplify', 'extract', 'consolidate'],
    'feature': ['feature', 'implement', 'add', 'support'],
    'bug': ['bug', 'fix', 'error', 'issue', 'broken'],
    'architecture': ['architecture', 'design', 'pattern', 'service'],
}

# Files to exclude
EXCLUDE_PATTERNS = [
    r'node_modules',
    r'\.git',
    r'\.venv',
    r'venv',
    r'__pycache__',
    r'\.pytest_cache',
    r'\.mypy_cache',
    r'\.tox',
    r'dist',
    r'build',
    r'\.next',
    r'coverage',
    r'\.playwright',
    r'tokenizer\.json',  # Large tokenizer files
    r'checkpoint-',  # ML model checkpoints
    r'\.md$',  # Documentation files (we'll handle separately)
    r'\.json$',  # JSON config files (usually not code)
    r'\.yml$',  # YAML config files
    r'\.yaml$',  # YAML config files
    r'\.txt$',  # Text files
    r'\.log$',  # Log files
]

# Code file extensions
CODE_EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}


@dataclass
class TechnicalDebtItem:
    """Represents a single TODO/FIXME comment."""
    file_path: str
    line_number: int
    comment_type: str  # TODO, FIXME, XXX, HACK
    message: str
    priority: str = 'medium'
    category: str = 'other'
    context: str = ''  # Surrounding code context
    
    def __post_init__(self):
        """Auto-categorize based on message content."""
        message_lower = self.message.lower()
        
        # Determine priority
        for priority, keywords in PRIORITY_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                self.priority = priority
                break
        
        # Determine category
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                self.category = category
                break


def should_exclude_file(file_path: str) -> bool:
    """Check if file should be excluded from analysis."""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    return False


def extract_comments_from_file(file_path: Path) -> List[TechnicalDebtItem]:
    """Extract TODO/FIXME comments from a single file."""
    items = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Get file extension
        ext = file_path.suffix.lower()
        
        # Combine all lines for context
        full_text = ''.join(lines)
        
        # Find all TODO/FIXME comments
        for pattern in TODO_PATTERNS:
            for match in re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE):
                comment_type = match.group(0).split(':')[0].strip().upper()
                message = match.group(1).strip() if match.group(1) else ''
                
                # Find line number
                line_num = full_text[:match.start()].count('\n') + 1
                
                # Get context (3 lines before and after)
                context_lines = []
                start = max(0, line_num - 4)
                end = min(len(lines), line_num + 3)
                for i in range(start, end):
                    context_lines.append(f"{i+1:4d}: {lines[i].rstrip()}")
                context = '\n'.join(context_lines)
                
                item = TechnicalDebtItem(
                    file_path=str(file_path.relative_to(Path.cwd())),
                    line_number=line_num,
                    comment_type=comment_type,
                    message=message,
                    context=context
                )
                items.append(item)
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return items


def scan_codebase(root_dir: Path) -> List[TechnicalDebtItem]:
    """Scan codebase for TODO/FIXME comments."""
    all_items = []
    
    print(f"Scanning codebase in {root_dir}...")
    
    # Scan code files
    for ext in CODE_EXTENSIONS:
        for file_path in root_dir.rglob(f'*{ext}'):
            if should_exclude_file(str(file_path)):
                continue
            
            items = extract_comments_from_file(file_path)
            all_items.extend(items)
            if items:
                print(f"  Found {len(items)} items in {file_path.relative_to(root_dir)}")
    
    return all_items


def categorize_items(items: List[TechnicalDebtItem]) -> Dict[str, List[TechnicalDebtItem]]:
    """Categorize items by priority and category."""
    categorized = defaultdict(list)
    
    for item in items:
        key = f"{item.priority}_{item.category}"
        categorized[key].append(item)
    
    return categorized


def generate_backlog_report(items: List[TechnicalDebtItem], output_file: Path):
    """Generate a markdown backlog report."""
    
    # Sort by priority (critical > high > medium > low)
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    items_sorted = sorted(items, key=lambda x: (
        priority_order.get(x.priority, 99),
        x.category,
        x.file_path,
        x.line_number
    ))
    
    # Group by priority
    by_priority = defaultdict(list)
    by_category = defaultdict(list)
    by_type = defaultdict(list)
    
    for item in items:
        by_priority[item.priority].append(item)
        by_category[item.category].append(item)
        by_type[item.comment_type].append(item)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Technical Debt Backlog\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Items:** {len(items)}\n\n")
        
        # Summary statistics
        f.write("## Summary Statistics\n\n")
        f.write("### By Priority\n\n")
        for priority in ['critical', 'high', 'medium', 'low']:
            count = len(by_priority[priority])
            f.write(f"- **{priority.upper()}:** {count} items\n")
        
        f.write("\n### By Category\n\n")
        for category in sorted(by_category.keys()):
            count = len(by_category[category])
            f.write(f"- **{category}:** {count} items\n")
        
        f.write("\n### By Type\n\n")
        for comment_type in sorted(by_type.keys()):
            count = len(by_type[comment_type])
            f.write(f"- **{comment_type}:** {count} items\n")
        
        # Top 50 high-priority items
        f.write("\n## Top 50 High-Priority Items\n\n")
        high_priority = [item for item in items_sorted if item.priority in ['critical', 'high']]
        top_50 = high_priority[:50]
        
        for i, item in enumerate(top_50, 1):
            f.write(f"### {i}. [{item.priority.upper()}] {item.comment_type}: {item.message[:100]}\n\n")
            f.write(f"**File:** `{item.file_path}` (line {item.line_number})\n\n")
            f.write(f"**Category:** {item.category}\n\n")
            if item.context:
                f.write("**Context:**\n```\n")
                f.write(item.context)
                f.write("\n```\n\n")
            f.write("---\n\n")
        
        # All items by priority
        f.write("\n## All Items by Priority\n\n")
        for priority in ['critical', 'high', 'medium', 'low']:
            priority_items = [item for item in items_sorted if item.priority == priority]
            if not priority_items:
                continue
            
            f.write(f"### {priority.upper()} Priority ({len(priority_items)} items)\n\n")
            
            # Group by category
            by_cat = defaultdict(list)
            for item in priority_items:
                by_cat[item.category].append(item)
            
            for category in sorted(by_cat.keys()):
                cat_items = by_cat[category]
                f.write(f"#### {category.upper()} ({len(cat_items)} items)\n\n")
                
                for item in cat_items[:20]:  # Limit to 20 per category
                    f.write(f"- **{item.comment_type}** in `{item.file_path}:{item.line_number}`: {item.message[:150]}\n")
                
                if len(cat_items) > 20:
                    f.write(f"- *... and {len(cat_items) - 20} more items*\n")
                
                f.write("\n")
            
            f.write("\n")
        
        # Recommendations
        f.write("\n## Recommendations\n\n")
        f.write("### Immediate Actions (Week 1-2)\n\n")
        critical_count = len(by_priority['critical'])
        high_count = len(by_priority['high'])
        f.write(f"1. **Address {critical_count} critical items** - Security, bugs, data loss risks\n")
        f.write(f"2. **Review {high_count} high-priority items** - Production issues, performance\n")
        f.write("3. **Create GitHub issues** for top 50 items\n")
        f.write("4. **Set up tracking** - Use project board or issue labels\n\n")
        
        f.write("### Short-term (Month 1)\n\n")
        f.write("1. **Address top 50 high-priority items**\n")
        f.write("2. **Categorize remaining items** by service/module\n")
        f.write("3. **Create service-specific backlogs**\n")
        f.write("4. **Set up automated tracking** - Prevent new debt accumulation\n\n")
        
        f.write("### Long-term (Quarter 1)\n\n")
        f.write("1. **Reduce technical debt by 10%** per quarter\n")
        f.write("2. **Establish code review standards** - Prevent new TODOs\n")
        f.write("3. **Regular backlog reviews** - Monthly prioritization\n")
        f.write("4. **Documentation improvements** - Address doc-related TODOs\n\n")


def main():
    """Main entry point."""
    root_dir = Path.cwd()
    output_file = root_dir / 'implementation' / 'technical-debt' / 'TECHNICAL_DEBT_BACKLOG.md'
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("Extracting technical debt from codebase...")
    items = scan_codebase(root_dir)
    
    print(f"\nFound {len(items)} TODO/FIXME items")
    
    if items:
        print(f"\nGenerating backlog report to {output_file}...")
        generate_backlog_report(items, output_file)
        print(f"✅ Backlog report generated: {output_file}")
        
        # Print summary
        by_priority = defaultdict(int)
        for item in items:
            by_priority[item.priority] += 1
        
        print("\nSummary:")
        for priority in ['critical', 'high', 'medium', 'low']:
            count = by_priority[priority]
            print(f"  {priority.upper()}: {count} items")
    else:
        print("No TODO/FIXME items found in code files.")


if __name__ == '__main__':
    main()

