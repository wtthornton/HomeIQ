# GitHub Repository Crawler Implementation

**Date:** 2025-11-21  
**Status:** ✅ Complete and Tested

---

## Summary

Successfully implemented GitHub repository crawler for Home Assistant blueprint repositories. The crawler can discover and index blueprints from GitHub repositories, significantly expanding the blueprint corpus.

---

## Implementation Details

### Files Created/Modified

1. **`services/automation-miner/src/miner/github_client.py`** (NEW)
   - GitHub API client with rate limiting
   - Repository crawling functionality
   - Recursive blueprint file discovery
   - Blueprint extraction and parsing

2. **`services/automation-miner/src/cli.py`** (MODIFIED)
   - Added `crawl-github` command
   - Added `run_github_crawl()` function
   - Integrated GitHub client with existing parser

### Features

- **GitHub API Integration**: Async HTTP client with rate limiting
- **Recursive File Discovery**: Automatically finds all blueprint YAML files in repositories
- **Blueprint Detection**: Identifies files containing `blueprint:` key
- **Parser Compatibility**: Converts GitHub blueprint format to parser-compatible format
- **Error Handling**: Graceful handling of rate limits and API errors
- **Dry Run Support**: Test crawls without saving to database

---

## Testing Results

### Test Repository: SirGoodenough/HA_Blueprints

**Results:**
- **Blueprints Found**: 33
- **Successfully Parsed**: 30
- **Failed**: 3 (validation errors with condition handling)
- **Rate Limited**: 3 files (hit GitHub API limits)

**Before Crawl:**
- Total automations: 51
- Blueprints: 9

**After Crawl:**
- Total automations: 81 (+30)
- Blueprints: 28 (+19)

---

## Usage

### CLI Command

```bash
# Dry run (test without saving)
docker exec automation-miner python -m src.cli crawl-github \
  --owner SirGoodenough \
  --repo HA_Blueprints \
  --dry-run

# Real crawl (save to database)
docker exec automation-miner python -m src.cli crawl-github \
  --owner SirGoodenough \
  --repo HA_Blueprints

# Update existing records
docker exec automation-miner python -m src.cli crawl-github \
  --owner SirGoodenough \
  --repo HA_Blueprints \
  --update-existing
```

### Identified Repositories to Crawl

1. **SirGoodenough/HA_Blueprints** ✅ (Tested - 33 blueprints)
2. **EPMatt/awesome-ha-blueprints** (Pending)
3. **TheFes/ha-blueprints** (Pending)
4. **airalab/home-assistant-blueprints** (Pending)

---

## Known Issues

1. **Rate Limiting**: GitHub API rate limits (60 requests/hour without token, 5000/hour with token)
   - **Solution**: Add `GITHUB_TOKEN` environment variable for higher rate limits
   - Current implementation waits 60 seconds when rate limited

2. **Validation Errors**: Some blueprints fail validation due to `!input` tags in conditions
   - **Impact**: Minor - 3 blueprints failed out of 33
   - **Fix Needed**: Improve parser to handle `!input` tags in condition arrays

3. **Multi-Document YAML**: Some repositories have multiple YAML documents in single files
   - **Impact**: Some files can't be parsed
   - **Fix Needed**: Support parsing multiple YAML documents

---

## Next Steps

### Immediate
1. **Crawl Additional Repositories**
   - EPMatt/awesome-ha-blueprints (curated collection)
   - TheFes/ha-blueprints (voice commands)
   - airalab/home-assistant-blueprints (various automations)

2. **Add GitHub Token Support**
   - Configure `GITHUB_TOKEN` environment variable
   - Increase rate limits from 60/hour to 5000/hour

### Improvements
1. **Parser Enhancements**
   - Better handling of `!input` tags in arrays
   - Support for multi-document YAML files

2. **Batch Repository Crawling**
   - CLI command to crawl multiple repositories
   - Configuration file for repository list

3. **HA Blueprint Hub Integration**
   - Investigate API or scraping capabilities
   - Extract blueprint URLs from hablueprints.directory (171+ blueprints)

---

## Configuration

### Environment Variables

```bash
# Optional: GitHub API token for higher rate limits
GITHUB_TOKEN=ghp_your_token_here

# Minimum stars threshold (currently not enforced)
GITHUB_MIN_STARS=50
```

### Rate Limits

- **Without Token**: 60 requests/hour (unauthenticated)
- **With Token**: 5,000 requests/hour (authenticated)
- **Current Rate**: ~5 requests/second (conservative)

---

## Statistics

**Corpus Growth:**
- Before: 51 automations (9 blueprints)
- After GitHub crawl: 81 automations (28 blueprints)
- **Increase**: +30 automations (+19 blueprints)

**Potential Additional Sources:**
- HA Blueprint Hub: 171+ blueprints
- GitHub Repositories: Estimated 50-200+ additional blueprints
- Community Forums: Thousands (dynamic)

---

## References

- GitHub API Documentation: https://docs.github.com/en/rest
- Repository Research: `implementation/BLUEPRINT_REPOSITORIES_RESEARCH.md`
- Blueprint API Documentation: `services/automation-miner/BLUEPRINT_API.md`

---

**Status:** ✅ Implementation complete and tested successfully





