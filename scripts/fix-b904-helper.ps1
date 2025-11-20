# Script to help fix B904 issues (exception handling)
# This script identifies patterns and suggests fixes

Write-Host "B904 Fix Helper Script`n" -ForegroundColor Cyan
Write-Host "Pattern 1: except ValueError:" -ForegroundColor Yellow
Write-Host "  Fix: except ValueError as err:" -ForegroundColor Green
Write-Host "       raise ... from err`n" -ForegroundColor Green

Write-Host "Pattern 2: except Exception as e:" -ForegroundColor Yellow
Write-Host "  Fix: raise ... from e`n" -ForegroundColor Green

Write-Host "Pattern 3: except SomeException:" -ForegroundColor Yellow
Write-Host "  Fix: except SomeException as err:" -ForegroundColor Green
Write-Host "       raise ... from err`n" -ForegroundColor Green

Write-Host "Running ruff to find B904 issues..." -ForegroundColor Cyan
python -m ruff check --select B904 services/ --output-format=concise 2>&1 | Select-Object -First 20
