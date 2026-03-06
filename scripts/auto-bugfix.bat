@echo off
REM auto-bugfix.bat — Windows launcher for auto-bugfix.ps1
REM Usage: scripts\auto-bugfix.bat [--bugs N] [--branch NAME] [--target-dir PATH]

where pwsh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    pwsh -ExecutionPolicy Bypass -File "%~dp0auto-bugfix.ps1" %*
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0auto-bugfix.ps1" %*
)
