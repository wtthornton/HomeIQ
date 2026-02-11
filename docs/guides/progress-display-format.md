# Progress Display Format - Documentation

**Created:** February 5, 2026
**Purpose:** Document the terminal-style progress display format used in HomeIQ rebuild status reporting

---

## What Is This?

The progress display format is a **visual status reporting technique** that presents complex multi-phase project status in a clear, scannable, terminal-style format. It's particularly effective for:

- Multi-phase project tracking
- Service rebuild status
- CI/CD pipeline visualization
- Migration progress monitoring

---

## Example Output

```
📊 Progress Summary

Phase 0: Pre-Deployment  ✅ [██████████] 100% COMPLETE
Phase 1: Batch Rebuild   ✅ [██████████] 100% COMPLETE
Phase 2: Std Libraries   📋 [          ] 0% READY (Planning: 100%)
Phase 3: ML/AI           ⏳ [          ] 0% PENDING
Phase 4: Testing         ⏳ [          ] 0% PENDING
Phase 5: Deployment      ⏳ [          ] 0% PENDING
Phase 6: Validation      ⏳ [          ] 0% PENDING

TOTAL: 33.3% complete (2/6 phases)
Phase 2 Planning: 100% complete, ready for execution
```

---

## How It Works

### 1. **Format Type: Plain Text in Code Block**

This is **NOT** a special tool or library - it's standard markdown rendered in a code block:

```markdown
```
Phase 0: Pre-Deployment  ✅ [██████████] 100% COMPLETE
Phase 1: Batch Rebuild   ✅ [██████████] 100% COMPLETE
Phase 2: Std Libraries   📋 [          ] 0% READY
```
```

### 2. **Key Components**

#### **Status Icons** (Emojis)
- ✅ - Complete/Success
- 📋 - Ready to start
- ⏳ - Pending/Waiting
- 🔄 - In progress
- ❌ - Failed/Error
- ⚠️ - Warning

#### **Progress Bars** (Unicode Block Characters)
- `[██████████]` - 100% complete (10 blocks)
- `[█████     ]` - 50% complete (5 blocks)
- `[          ]` - 0% complete (10 spaces)

Unicode characters used:
- `█` (U+2588) - Full block
- ` ` (U+0020) - Space

#### **Status Labels**
- COMPLETE - Phase finished successfully
- READY - Planning complete, ready to execute
- PENDING - Waiting for prerequisites
- IN PROGRESS - Currently executing
- FAILED - Encountered errors

### 3. **Formatting Rules**

#### **Column Alignment**
```
Phase 0: Pre-Deployment  ✅ [██████████] 100% COMPLETE
         ^20 chars       ^2  ^12 chars   ^4   ^label
Phase 1: Batch Rebuild   ✅ [██████████] 100% COMPLETE
         ^20 chars       ^2  ^12 chars   ^4   ^label
```

- **Phase Name:** Left-aligned, padded to ~20 characters
- **Icon:** 2 characters (emoji + space)
- **Progress Bar:** Fixed 12 characters `[` + 10 blocks/spaces + `]`
- **Percentage:** Right-aligned, 4 characters (e.g., "100%")
- **Status:** Uppercase label

#### **Indentation for Sub-Items**
```
Phase 1: Batch Rebuild ✅ [██████████] 100% COMPLETE
  └─ Services: 38/40 ✅ (95% success)
  └─ Duration: 1 day
  └─ Status: All critical services healthy
```

Use `└─` (box drawing characters) for tree structure:
- `└` (U+2514) - Box drawings light up and right
- `─` (U+2500) - Box drawings light horizontal

---

## Why This Format?

### **Advantages**

1. **Instant Visual Scan**
   - Icons provide immediate status understanding
   - Progress bars show completion at a glance
   - Color-free (works in any terminal/text environment)

2. **Hierarchical Information**
   - Main phases at top level
   - Sub-items indented with tree characters
   - Easy to scan top-down

3. **Consistent Width**
   - Fixed column widths prevent wrapping
   - Aligns well in code blocks
   - Works in terminals, markdown, text files

4. **Copy-Paste Friendly**
   - Plain text - works anywhere
   - No HTML, no special rendering
   - Can be pasted into Slack, Discord, GitHub, etc.

5. **Version Control Friendly**
   - Text-based status can be committed to git
   - Diffs show progress changes clearly
   - No binary images or complex markup

### **Comparison to Alternatives**

| Format | Visual | Terminal | Git-Friendly | Copy-Paste | Setup |
|--------|--------|----------|--------------|------------|-------|
| **This Format** | ✅ Good | ✅ Perfect | ✅ Yes | ✅ Yes | None |
| HTML Progress | ✅ Great | ❌ No | ❌ No | ⚠️ Partial | Medium |
| SVG Badges | ✅ Great | ❌ No | ⚠️ Partial | ❌ No | High |
| Plain Text | ⚠️ Basic | ✅ Yes | ✅ Yes | ✅ Yes | None |
| Rich UI | ✅ Excellent | ❌ No | ❌ No | ❌ No | High |

---

## Implementation Guide

### **Creating Progress Bars**

```python
def create_progress_bar(percentage: float, width: int = 10) -> str:
    """
    Create ASCII progress bar.

    Args:
        percentage: 0-100 completion percentage
        width: Total width of bar (default 10 characters)

    Returns:
        Progress bar string like "[█████     ]"
    """
    filled = int((percentage / 100) * width)
    empty = width - filled

    bar = "█" * filled + " " * empty
    return f"[{bar}]"

# Examples
print(create_progress_bar(0))    # [          ]
print(create_progress_bar(50))   # [█████     ]
print(create_progress_bar(100))  # [██████████]
```

### **Creating Status Lines**

```python
def create_status_line(
    phase_name: str,
    percentage: float,
    status: str,
    icon: str = "⏳"
) -> str:
    """
    Create formatted status line.

    Args:
        phase_name: Name of phase (e.g., "Phase 1: Batch Rebuild")
        percentage: 0-100 completion percentage
        status: Status label (e.g., "COMPLETE", "PENDING")
        icon: Status icon (default: ⏳)

    Returns:
        Formatted status line
    """
    # Pad phase name to consistent width
    padded_name = phase_name.ljust(20)

    # Create progress bar
    bar = create_progress_bar(percentage)

    # Format percentage
    pct = f"{int(percentage):3d}%"

    return f"{padded_name} {icon} {bar} {pct} {status}"

# Examples
print(create_status_line("Phase 0: Prep", 100, "COMPLETE", "✅"))
# Phase 0: Prep         ✅ [██████████] 100% COMPLETE

print(create_status_line("Phase 1: Build", 50, "IN PROGRESS", "🔄"))
# Phase 1: Build        🔄 [█████     ]  50% IN PROGRESS

print(create_status_line("Phase 2: Test", 0, "PENDING", "⏳"))
# Phase 2: Test         ⏳ [          ]   0% PENDING
```

### **Complete Status Report**

```python
def generate_status_report(phases: list[dict]) -> str:
    """
    Generate complete status report.

    Args:
        phases: List of phase dictionaries with keys:
                - name: Phase name
                - percentage: Completion percentage
                - status: Status label
                - icon: Status icon
                - sub_items: Optional list of sub-items

    Returns:
        Complete formatted status report
    """
    lines = ["📊 Progress Summary", ""]

    completed_phases = 0
    total_phases = len(phases)

    for phase in phases:
        # Add main phase line
        line = create_status_line(
            phase["name"],
            phase["percentage"],
            phase["status"],
            phase.get("icon", "⏳")
        )
        lines.append(line)

        # Count completed phases
        if phase["percentage"] == 100:
            completed_phases += 1

        # Add sub-items if present
        for sub_item in phase.get("sub_items", []):
            lines.append(f"  └─ {sub_item}")

    # Add summary
    overall_pct = (completed_phases / total_phases) * 100
    lines.append("")
    lines.append(f"TOTAL: {overall_pct:.1f}% complete ({completed_phases}/{total_phases} phases)")

    return "\n".join(lines)

# Example usage
phases = [
    {
        "name": "Phase 0: Prep",
        "percentage": 100,
        "status": "COMPLETE",
        "icon": "✅",
        "sub_items": ["Stories: 5/5 ✅", "Duration: 3 hours"]
    },
    {
        "name": "Phase 1: Build",
        "percentage": 100,
        "status": "COMPLETE",
        "icon": "✅",
        "sub_items": ["Services: 38/40 ✅", "Duration: 1 day"]
    },
    {
        "name": "Phase 2: Libraries",
        "percentage": 0,
        "status": "READY",
        "icon": "📋",
        "sub_items": ["Stories: 0/7", "Planning: 100%"]
    }
]

print(generate_status_report(phases))
```

---

## Real-World Usage Examples

### **1. HomeIQ Rebuild Status** (Current Usage)

```
📊 Progress Summary

Phase 0: Pre-Deployment  ✅ [██████████] 100% COMPLETE
  └─ Stories: 5/5 ✅
  └─ Duration: 3 hours
  └─ Status: All validation passed

Phase 1: Batch Rebuild   ✅ [██████████] 100% COMPLETE
  └─ Services: 38/40 ✅ (95% success)
  └─ Duration: 1 day
  └─ Status: All critical services healthy

Phase 2: Std Libraries   📋 [          ] 0% READY (Planning: 100%)
  └─ Stories: 0/7
  └─ Est. Duration: 5-7 days
  └─ Status: Ready to start

TOTAL: 33.3% complete (2/6 phases)
Phase 2 Planning: 100% complete, ready for execution
```

### **2. Service Health Dashboard**

```
🏥 Service Health Status

api-automation-edge    ✅ [██████████] 100% HEALTHY   Uptime: 20h
ai-automation-ui       ✅ [██████████] 100% HEALTHY   Uptime: 30m
ml-service            ✅ [██████████] 100% HEALTHY   Uptime: 21h
data-api              ✅ [██████████] 100% HEALTHY   Uptime: 22h
websocket-ingestion   ⚠️ [████████  ]  80% DEGRADED  Uptime: 21h

TOTAL: 43/43 services running (95.3% healthy)
```

### **3. Migration Progress**

```
🔄 Database Migration Status

Step 1: Backup          ✅ [██████████] 100% COMPLETE   2.3 GB backed up
Step 2: Schema Changes  ✅ [██████████] 100% COMPLETE   15 tables updated
Step 3: Data Migration  🔄 [███████   ]  70% IN PROGRESS   7/10 tables
Step 4: Validation      ⏳ [          ]   0% PENDING   Waiting...
Step 5: Cleanup         ⏳ [          ]   0% PENDING   Waiting...

TOTAL: 54% complete (2.7/5 steps)
ETA: 15 minutes remaining
```

### **4. CI/CD Pipeline**

```
🚀 Deployment Pipeline

Build              ✅ [██████████] 100% COMPLETE   3m 42s
Test               ✅ [██████████] 100% COMPLETE   5m 18s
Security Scan      ✅ [██████████] 100% COMPLETE   1m 23s
Deploy Staging     🔄 [██████    ]  60% IN PROGRESS
Deploy Production  ⏳ [          ]   0% PENDING

TOTAL: 72% complete
Current: Deploying to staging (3/5 instances)
```

---

## Integration with Tools

### **1. Shell Scripts**

```bash
#!/bin/bash
# progress-display.sh

print_progress() {
    local name=$1
    local pct=$2
    local status=$3
    local icon=$4

    # Calculate filled blocks
    local filled=$((pct / 10))
    local empty=$((10 - filled))

    # Create bar
    local bar="["
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+=" "; done
    bar+="]"

    # Print formatted line
    printf "%-20s %s %s %3d%% %s\n" "$name" "$icon" "$bar" "$pct" "$status"
}

# Usage
echo "📊 Progress Summary"
echo ""
print_progress "Phase 0: Prep" 100 "COMPLETE" "✅"
print_progress "Phase 1: Build" 100 "COMPLETE" "✅"
print_progress "Phase 2: Test" 0 "PENDING" "⏳"
```

### **2. Python Status File**

Save status to file for tracking:

```python
import json
from datetime import datetime

def save_status_snapshot(phases: list[dict], filename: str = "status.txt"):
    """Save current status to file with timestamp."""
    report = generate_status_report(phases)
    timestamp = datetime.now().isoformat()

    with open(filename, "a") as f:
        f.write(f"\n=== Status Snapshot: {timestamp} ===\n")
        f.write(report)
        f.write("\n")

# Can be committed to git for history tracking
```

### **3. GitHub Actions / GitLab CI**

```yaml
# .github/workflows/deploy.yml
- name: Display Progress
  run: |
    echo "📊 Deployment Progress"
    echo ""
    echo "Build              ✅ [██████████] 100% COMPLETE"
    echo "Test               ✅ [██████████] 100% COMPLETE"
    echo "Deploy Staging     🔄 [█████     ]  50% IN PROGRESS"
```

---

## Best Practices

### **Do's ✅**

1. **Keep column widths consistent** - Makes scanning easier
2. **Use meaningful icons** - Icons should be intuitive
3. **Include sub-items for context** - Helps understand what's complete
4. **Add summary line** - Overall percentage helps track progress
5. **Update timestamps** - Show when status was last updated
6. **Use in code blocks** - Preserves formatting in markdown

### **Don'ts ❌**

1. **Don't mix fonts** - Stick to monospace in code blocks
2. **Don't use too many colors** - Keep it simple (emojis are enough)
3. **Don't make bars too long** - 10-20 characters is optimal
4. **Don't update too frequently** - Status should be meaningful changes
5. **Don't nest too deep** - 2-3 levels max for readability

---

## Comparison to AI quality tools

### **Is This Part of AI quality tools?**

**No** - This is a **display formatting technique**, not a AI quality tools feature.

| Aspect | AI quality tools | This Format |
|--------|-------------------|-------------|
| **What it is** | Agent orchestration framework | Visual status display technique |
| **Purpose** | Coordinate skills, manage workflows | Present status information clearly |
| **Technology** | Python framework with agents | Plain text + markdown + emojis |
| **Dependencies** | ai-tools package | None (standard text) |
| **Usage** | `workflow`, `@planner`, etc. | Copy-paste, shell scripts, markdown |

### **How They Complement Each Other**

- **AI quality tools:** Executes the work (planning, coding, testing)
- **Progress Display:** Shows the status of that work visually

**Example Integration:**
```python
# AI quality tools generates the status data
status = simple_mode.get_workflow_status()

# Progress display formats it for humans
report = generate_status_report(status["phases"])
print(report)
```

---

## Future Enhancements

### **Possible Additions**

1. **Color Support** (with ANSI codes for terminals)
2. **Animated Progress** (for real-time updates)
3. **Sparkline Charts** (for historical trends)
4. **Tree Expansion** (collapsible sections)
5. **Time Estimates** (remaining time calculations)

### **Example: Colored Terminal Output**

```python
# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def colored_status_line(name, pct, status, icon):
    color = GREEN if pct == 100 else YELLOW if pct > 0 else RESET
    return f"{color}{create_status_line(name, pct, status, icon)}{RESET}"
```

---

## Conclusion

This progress display format provides:
- ✅ **Clarity:** Instant visual understanding
- ✅ **Simplicity:** Plain text, no dependencies
- ✅ **Portability:** Works everywhere (terminals, markdown, chat)
- ✅ **Maintainability:** Easy to update and version control

**Perfect for:**
- Multi-phase project tracking (like HomeIQ rebuild)
- CI/CD pipeline visualization
- Service health monitoring
- Migration progress reporting

**Origin:** Created organically during HomeIQ Phase 1/2 status reporting as an effective way to communicate complex multi-phase progress.

---

**Status:** ✅ Documented
**Version:** 1.0.0
**Created:** February 5, 2026
