@echo off
REM HA Event Logger Runner - Batch version
REM Simple script to run the HA event logger for baseline measurement

echo 🔍 HA Event Logger - Baseline Measurement Tool
echo ================================================

REM Check if HA token is provided
if "%HA_ACCESS_TOKEN%"=="" (
    REM Try to load from .env files
    set TOKEN_FOUND=0
    for %%f in (.env infrastructure\.env infrastructure\env.production) do (
        if exist "%%f" (
            echo 📄 Found .env file: %%f
            for /f "tokens=1,2 delims==" %%a in ('findstr "HOME_ASSISTANT_TOKEN" "%%f"') do (
                set HA_ACCESS_TOKEN=%%b
                set TOKEN_FOUND=1
                echo ✅ Found HOME_ASSISTANT_TOKEN in %%f
            )
        )
    )
    
    if "%TOKEN_FOUND%"=="0" (
        echo ❌ Error: Home Assistant token not found
        echo 💡 Options:
        echo    1. Set environment variable: set HA_ACCESS_TOKEN=your_token
        echo    2. Add HOME_ASSISTANT_TOKEN=your_token to .env file
        echo    3. Checked .env files: .env, infrastructure\.env, infrastructure\env.production
        pause
        exit /b 1
    )
)

echo 🔗 HA URL: %HA_WEBSOCKET_URL%
echo ⏱️  Duration: %LOG_DURATION_MINUTES% minutes
echo 📊 This will establish baseline event volume from your HA instance
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.7+
    pause
    exit /b 1
)

echo 🐍 Python found
echo 📦 Checking dependencies...

REM Check if required packages are installed
python -c "import aiohttp" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing aiohttp...
    pip install aiohttp
)

echo 🚀 Starting HA Event Logger...
echo.

REM Run the event logger
python tests\ha_event_logger.py

echo.
echo ✅ Event logging completed!
echo 📄 Check 'ha_events.log' for detailed logs
pause
