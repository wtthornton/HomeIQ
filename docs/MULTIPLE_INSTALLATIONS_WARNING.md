# Multiple TappsCodingAgents Installations Warning

## Problem

When you have **multiple copies** of TappsCodingAgents on your system and one is installed in **editable mode**, Python will always import from the editable install location, regardless of which directory you run commands from.

## Example Scenario

You have two directories:
- `C:\cursor\TappsCodingAgents` (installed in editable mode)
- `C:\cursor\HomeIQ\TappsCodingAgents` (not installed)

When you run:
```powershell
cd C:\cursor\HomeIQ
python -m tapps_agents.cli init
```

Python will still import `tapps_agents` from `C:\cursor\TappsCodingAgents` because that's the editable install location in `sys.path`.

## Why This Happens

When a package is installed in editable mode (`pip install -e .`), Python adds it to `sys.path` as an editable path hook (e.g., `__editable__.tapps_agents-3.0.1.finder.__path_hook__`). Python imports from this location **first**, regardless of your current working directory.

## Symptoms

- Running `tapps_agents.cli` from different directories still imports from the same location
- `ModuleNotFoundError` errors that reference paths in a different directory
- Version mismatches when you expect to use code from one directory but Python uses another

## Solutions

### Option 1: Fix the Editable Install (Recommended)

If the editable install is broken (e.g., `ModuleNotFoundError`), reinstall it:

```powershell
cd C:\cursor\TappsCodingAgents
pip uninstall -y tapps-agents
pip install -e .
```

### Option 2: Use Virtual Environments

Use separate virtual environments for each project to isolate installations:

```powershell
# For TappsCodingAgents development
cd C:\cursor\TappsCodingAgents
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# For HomeIQ project
cd C:\cursor\HomeIQ
python -m venv .venv
.venv\Scripts\activate
# Don't install TappsCodingAgents here, or install a specific version
```

### Option 3: Verify Which Package is Being Used

Check which `tapps_agents` Python is importing:

```powershell
python -c "import tapps_agents; import inspect; print(f'Version: {tapps_agents.__version__}'); print(f'Location: {inspect.getfile(tapps_agents)}')"
```

This will show you:
- The version being used
- The file path (which directory it's coming from)

## Best Practices

1. **One editable install per system/user**: Only install TappsCodingAgents in editable mode from one location
2. **Use virtual environments**: Isolate projects with their own environments
3. **Verify before installing**: Check if TappsCodingAgents is already installed before running `pip install -e .`
4. **Check sys.path**: Understand which package Python will import before running commands

## Related Issues

- [UPGRADE_REINSTALL_REQUIRED.md](UPGRADE_REINSTALL_REQUIRED.md) - Issues after upgrading versions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting guide

