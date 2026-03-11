You are a senior {{languages}} developer. Write unit tests for these bug fixes:

BUGS THAT WERE FIXED:
{{bugs_json}}

For each bug:
1. Read the fixed file to understand the fix.
2. Write a pytest test that would have FAILED before the fix and PASSES after.
3. Place tests in the appropriate tests/ directory near the source file.
4. Use pytest conventions: test_*.py files, test_* functions.
5. Mock external dependencies (databases, APIs, file I/O).

After writing tests, run: pytest <test_file> -v --tb=short to verify they pass.
Then run {{tapps_prefix}}tapps_quick_check on each test file.
