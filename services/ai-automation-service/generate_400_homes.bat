@echo off
REM Generate 400 synthetic homes with OpenAI enhancement for testing
REM 
REM Configuration:
REM - 400 total homes
REM - 20% OpenAI enhancement (80 homes enhanced, 320 template-based)
REM - 7 days of events per home (faster than 90 days)
REM - All external data enabled (weather, carbon, pricing, calendar)

echo ========================================
echo Generating 400 Synthetic Homes
echo ========================================
echo.
echo Configuration:
echo   - Total homes: 400
echo   - OpenAI enhanced: 80 homes (20%%)
echo   - Template-based: 320 homes (80%%)
echo   - Events: 7 days per home
echo   - Output: tests/datasets/synthetic_homes_400_test
echo   - Rate limit: 20 RPM (3.3s delay between OpenAI calls)
echo.
echo Estimated time: 3-5 hours
echo Estimated cost: $0.40-1.60 (OpenAI API)
echo.
echo Rate limiting: Automatic delays prevent exceeding OpenAI thresholds
echo   - 3.3 seconds between API calls (20 RPM)
echo   - Exponential backoff on rate limit errors
echo   - Automatic retry with backoff
echo.
echo Starting generation...
echo.

cd /d %~dp0
python scripts/generate_synthetic_homes.py ^
    --count 400 ^
    --enable-openai ^
    --enhancement-percentage 0.20 ^
    --days 7 ^
    --output tests/datasets/synthetic_homes_400_test ^
    --rate-limit-rpm 20

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Generation Complete!
    echo ========================================
    echo.
    echo Homes saved to: tests/datasets/synthetic_homes_400_test
) else (
    echo.
    echo ========================================
    echo Generation Failed!
    echo ========================================
    echo.
    echo Check the error messages above.
    echo Make sure OPENAI_API_KEY is set in .env file.
)

pause

