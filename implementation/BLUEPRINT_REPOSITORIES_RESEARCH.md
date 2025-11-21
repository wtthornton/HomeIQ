# Home Assistant Blueprint Repositories Research

**Date:** 2025-11-21  
**Current Corpus:** 51 automations, 9 blueprints  
**Goal:** Identify additional blueprint repositories to expand corpus

---

## Executive Summary

### Verified Blueprint Counts

| Repository/Source | Blueprints | Status | Notes |
|-------------------|------------|--------|-------|
| **HA Blueprint Hub** | **171+** | ✅ Verified | Active directory, 430K+ downloads |
| **Home Assistant Community Forums** | **Unknown (1000s+)** | ✅ Crawling | 51 processed, 9 blueprints detected |
| **EPMatt/awesome-ha-blueprints** | Unknown | ⚠️ Needs Verification | Curated, actively maintained |
| **TheFes/ha-blueprints** | Unknown | ⚠️ Needs Verification | Voice command focused |
| **airalab/home-assistant-blueprints** | Unknown | ⚠️ Needs Verification | Various automation types |
| **SirGoodenough/HA_Blueprints** | Unknown | ⚠️ Needs Verification | Well documented |

**Total Verified:** 171+ blueprints  
**Total Estimated:** 171+ verified + 50-200+ from GitHub repos + 1000s from Community Forums  
**Current Corpus:** 51 automations (9 blueprints)

---

## Current Status

The automation-miner currently crawls from:
- **Home Assistant Community Blueprints Exchange (Discourse)**: Category 53
  - Current crawl: 51 automations
  - Blueprints detected: 9

---

## Additional Blueprint Sources Identified

### 1. GitHub Repositories

#### 1.1 **EPMatt/awesome-ha-blueprints**
- **URL:** https://github.com/EPMatt/awesome-ha-blueprints
- **Description:** Curated collection of automation blueprints for Home Assistant
- **Status:** Actively maintained, community-tested
- **Blueprint Count:** Unknown (needs verification)
- **Notes:** Repository focuses on reliable and customizable blueprints

#### 1.2 **TheFes/ha-blueprints**
- **URL:** https://github.com/TheFes/ha-blueprints
- **Description:** Blueprints designed for advanced voice commands using Assist
- **Status:** Active repository
- **Blueprint Count:** Unknown (needs verification)
- **Notes:** Specialized for voice command automation

#### 1.3 **airalab/home-assistant-blueprints**
- **URL:** https://github.com/airalab/home-assistant-blueprints
- **Description:** Variety of blueprints including Telegram bot notifications and motion sensor-controlled lighting
- **Status:** Active repository
- **Blueprint Count:** Unknown (needs verification)
- **Notes:** Includes climate control and notification blueprints

#### 1.4 **SirGoodenough/HA_Blueprints**
- **URL:** https://github.com/SirGoodenough/HA_Blueprints
- **Description:** Personal collection of automation and script blueprints
- **Status:** Active repository with detailed setup instructions
- **Blueprint Count:** Unknown (needs verification)
- **Notes:** Each blueprint includes detailed documentation

### 2. Online Directories

#### 2.1 **HA Blueprint Hub**
- **URL:** https://hablueprints.directory
- **Description:** Searchable directory of Home Assistant blueprints
- **Status:** Active platform
- **Blueprint Count:** **171+ blueprints** ✅ (Verified Nov 2025)
- **Statistics:**
  - 171+ community-created blueprints
  - 5 categories
  - 430,791+ total downloads
- **Popular Blueprints:**
  - "Advanced Heating Control V5": 5,600+ imports
  - "Binary Sensor Notification": 1,700+ imports
  - "Entity State Notification": 4,500+ imports
  - "Scene Based Theatre Mode": 5,900+ imports
- **Notes:** Provides detailed information about each blueprint including import counts. This is a significant source with 171+ verified blueprints.

### 3. Official Sources

#### 3.1 **Home Assistant Community Forums - Blueprints Exchange**
- **URL:** https://community.home-assistant.io/c/blueprints-exchange/53
- **Description:** Official forum category for blueprint sharing
- **Status:** Currently being crawled (51 automations processed)
- **Blueprint Count:** Dynamic, continuously growing
- **Notes:** This is the primary source currently being mined

---

## Recommended Next Steps

### Immediate Actions

1. **GitHub Repository Crawler Enhancement**
   - Implement GitHub API integration for blueprint repositories
   - Add support for crawling GitHub repositories with blueprint YAML files
   - Prioritize repositories listed above

2. **HA Blueprint Hub Integration**
   - Investigate API or scraping capabilities of hablueprints.directory
   - Extract blueprint URLs and metadata from the directory

3. **Repository Verification**
   - Visit each GitHub repository to count actual blueprint files
   - Determine file naming patterns and directory structures
   - Verify blueprint format consistency

### Implementation Priority

**Phase 1: GitHub Repository Crawler**
1. EPMatt/awesome-ha-blueprints (curated, high quality)
2. SirGoodenough/HA_Blueprints (well documented)
3. TheFes/ha-blueprints (specialized use case)
4. airalab/home-assistant-blueprints (variety)

**Phase 2: Directory Integration**
1. HA Blueprint Hub (hablueprints.directory) - API or scraping

**Phase 3: Extended Sources**
1. GitHub search for "blueprint:" language:YAML repositories
2. Additional community collections

---

## Summary of Blueprint Counts

| Source | Blueprints | Status | Notes |
|--------|-----------|--------|-------|
| **HA Blueprint Hub** | **171+** | ✅ Verified | Active directory with 430K+ downloads |
| **Home Assistant Community Forums** | **Unknown** | ✅ Currently Crawled | 51 automations processed, 9 blueprints detected |
| **EPMatt/awesome-ha-blueprints** | Unknown | Needs Verification | Curated collection, actively maintained |
| **TheFes/ha-blueprints** | Unknown | Needs Verification | Voice command focused |
| **airalab/home-assistant-blueprints** | Unknown | Needs Verification | Various automation types |
| **SirGoodenough/HA_Blueprints** | Unknown | Needs Verification | Well documented collection |

### Known Totals
- **HA Blueprint Hub**: 171+ blueprints ✅
- **Current Corpus**: 51 automations (9 blueprints) ✅

### Estimated Additional Potential
- **GitHub Repositories**: Unknown (likely 50-200+ additional blueprints across all repos)
- **Community Forums**: Hundreds to thousands (dynamic, growing)

## Estimation Notes

- **HA Blueprint Hub**: 171+ blueprints **verified** ✅
- **Repository sizes vary** significantly - need verification
- **Quality varies** - need curation/filtering
- **Maintenance status** varies - some may be archived

## Verification Required

Each repository should be verified for:
- Actual number of blueprint files
- File format and structure
- Maintenance status (last updated)
- Star/activity metrics
- Quality/curation level

---

## References

- Home Assistant Blueprint Documentation: https://www.home-assistant.io/docs/automation/using_blueprints/
- Community Blueprints Exchange: https://community.home-assistant.io/c/blueprints-exchange/53
- HA Blueprint Hub: https://hablueprints.directory

---

**Next Update:** After implementing GitHub crawler and verifying repository counts

