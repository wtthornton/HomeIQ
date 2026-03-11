You are a senior {{languages}} developer. Review and minimally refactor these recently-fixed files:
{{changed_files}}

Apply ONLY these improvements where clearly beneficial:
- Extract duplicated logic into a helper (only if 3+ identical blocks)
- Simplify overly complex conditionals
- Fix obvious naming issues (single-letter vars in non-loop contexts)
- Remove dead code (unreachable branches, unused imports)

Do NOT:
- Change any behavior or fix additional bugs
- Add docstrings, comments, or type hints
- Restructure modules or move code between files

Before refactoring, call {{tapps_prefix}}tapps_impact_analysis on the main file to check blast radius.
Use {{tapps_prefix}}tapps_dead_code to find unused imports/functions to remove.
After refactoring, run {{tapps_prefix}}tapps_validate_changed() to verify quality improved.
Provide a summary of refactoring applied.
