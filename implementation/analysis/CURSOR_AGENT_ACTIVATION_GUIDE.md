# Cursor Agent Activation Guide

**Issue:** When typing `@bmad-master`, the autocomplete dropdown appears, but if you don't select from it, your input gets deleted.

## Solutions

### Method 1: Select from Autocomplete (Easiest)
1. Type `@bmad-master`
2. When the dropdown appears, press **Enter** or **Tab** to accept the first suggestion
3. The agent will activate

### Method 2: Use Agent Dropdown
1. In the chat interface, click the **"Agent"** dropdown (infinity symbol icon)
2. Select **"bmad-master"** from the list
3. The agent will activate

### Method 3: Type and Send Immediately
1. Type `@bmad-master`
2. Immediately press **Enter** (don't wait for autocomplete)
3. This sends the message and activates the agent

### Method 4: Escape First
1. If autocomplete is interfering, press **Escape** to dismiss it
2. Type `@bmad-master` 
3. Press **Enter** to send

## Why This Happens

Cursor's autocomplete is designed to help you select files/agents, but it can be aggressive. When you type `@bmad-master`, it shows:
- `bmad-master.md` (agent definition)
- `bmad-master.mdc` (Cursor rule)
- Related templates and checklists

If you don't select one, Cursor assumes you're canceling and clears the input.

## Recommended Approach

**Use Method 1** - it's the most reliable:
1. Type `@bmad-master`
2. Press **Enter** when autocomplete appears
3. The agent activates and shows the help menu

## Verification

After activation, you should see:
- Agent greeting: "I'm @bmad-master, the universal task executor..."
- Automatic `*help` output showing numbered commands
- Plain text formatting (no markdown)

If you see markdown formatting or no automatic help, the activation didn't work correctly.

