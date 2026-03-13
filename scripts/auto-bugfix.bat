@echo off
REM auto-bugfix.bat — Windows launcher for auto-bugfix.ps1 (config-driven).
REM Uses homeiq-default.yaml by default. Pass -ConfigPath to override.
REM Usage: scripts\auto-bugfix.bat -Bugs 3
REM        scripts\auto-bugfix.bat -ConfigPath "path/to/config.yaml" -Bugs 5

where pwsh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    pwsh -ExecutionPolicy Bypass -File "%~dp0auto-bugfix.ps1" %*
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0auto-bugfix.ps1" %*
)
