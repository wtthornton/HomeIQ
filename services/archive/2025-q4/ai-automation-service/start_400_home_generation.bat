@echo off
REM Generate 400 synthetic homes with 30 days of events
REM All external data enabled (weather, carbon, pricing, calendar)

echo ========================================
echo Starting 400 Home Generation
echo ========================================
echo.
echo Configuration:
echo   - Total homes: 400
echo   - Events: 30 days per home
echo   - External data: All enabled
echo   - OpenAI enhancement: Disabled
echo   - Output: tests/datasets/synthetic_homes_400
echo.
echo Estimated time: 6-12 hours
echo.
echo Starting generation...
echo.

cd /d %~dp0
python scripts/generate_synthetic_homes.py --count 400 --days 30 --output tests/datasets/synthetic_homes_400 --enable-weather --enable-carbon --enable-pricing --enable-calendar

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Generation Complete!
    echo ========================================
    echo.
    echo Homes saved to: tests/datasets/synthetic_homes_400
) else (
    echo.
    echo ========================================
    echo Generation Failed!
    echo ========================================
    echo.
    echo Check the error messages above.
)

pause

