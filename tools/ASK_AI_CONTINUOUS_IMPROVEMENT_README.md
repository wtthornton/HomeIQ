# Ask AI Continuous Improvement Process

Automated testing and improvement cycle for Ask AI API that processes a complex WLED automation prompt through the full workflow (query → clarifications → approve), scores results, and iterates through 5 improvement cycles.

## Overview

This script automates the continuous improvement process for the Ask AI feature by:

1. Running the full Ask AI workflow with a test prompt
2. Scoring results based on automation correctness, YAML validity, and clarification count
3. Analyzing results and identifying improvement areas
4. Creating improvement plans
5. Deploying updated service (if improvements are made)
6. Repeating for 5 cycles
7. Generating a comprehensive summary

## Target Prompt

```
Every 15 mins choose a random effect on the Office WLED device. Play the effect for 15 secs. 
Choose random effect, random colors and brightness to 100%. At the end of the 15 sec the WLED 
light needs to return to exactly what it was before it started.
```

## Prerequisites

1. **Docker and Docker Compose** - Service must be deployable via docker-compose
2. **Python 3.8+** with required packages:
   - `httpx` - Async HTTP client
   - `pyyaml` - YAML validation
   - `asyncio` - Built-in async support

3. **Service Running** - The ai-automation-service must be accessible at `http://localhost:8024`

## Installation

Install required Python packages:

```bash
pip install httpx pyyaml
```

## Usage

### Basic Usage

```bash
python tools/ask-ai-continuous-improvement.py
```

### What It Does

1. **Cycle 1-5**: For each cycle:
   - Checks service health
   - Submits the target prompt to Ask AI API
   - Handles clarification questions automatically
   - Approves the best suggestion
   - Scores the results
   - Analyzes and creates improvement plan
   - Deploys service if improvements needed
   - Saves all data to `implementation/continuous-improvement/cycle-{N}/`

2. **Error Handling**:
   - Stops on API errors (4xx/5xx)
   - Stops on invalid YAML (score < 50)
   - Creates error reports for manual review

3. **Output**:
   - All cycle data saved to `implementation/continuous-improvement/cycle-{N}/`
   - Summary report: `implementation/continuous-improvement/SUMMARY.md`

## Output Structure

```
implementation/continuous-improvement/
├── cycle-1/
│   ├── query_response.json
│   ├── clarification_rounds.json
│   ├── clarification_response.json
│   ├── suggestion_selected.json
│   ├── approval_response.json
│   ├── automation.yaml
│   ├── score.json
│   ├── result.json
│   ├── logs.txt
│   ├── IMPROVEMENT_PLAN.md (if improvements needed)
│   └── ERROR_REPORT.md (if error occurred)
├── cycle-2/
│   └── ...
├── ...
└── SUMMARY.md
```

## Scoring System

### Automation Correctness (50% weight)
- 15-minute interval trigger (20 points)
- Random effect selection (15 points)
- 15-second duration (15 points)
- Brightness 100% (15 points)
- State restoration (20 points)
- Office WLED device entity (15 points)

### YAML Validity (30% weight)
- Valid YAML syntax (40 points)
- Required fields present (30 points)
- Valid HA structure (20 points)
- Valid entity IDs format (10 points)

### Clarification Count (20% weight)
- Score: 100 - (count * 10), minimum 0
- Lower clarification count = higher score

### Total Score
Weighted average: `(automation * 0.5) + (yaml * 0.3) + (clarifications * 0.2)`

## Success Metrics

- Automation correctness score > 80%
- YAML validity score = 100%
- Clarification rounds < 3
- Total score > 85%

## Error Handling

The script stops and creates an error report if:

1. **API Error**: HTTP 4xx/5xx response
   - Check service logs: `docker-compose logs ai-automation-service`
   - Fix the issue and re-run

2. **Invalid YAML**: YAML score < 50
   - Review generated YAML in `automation.yaml`
   - Fix YAML generation code
   - Deploy and re-run

3. **Service Unhealthy**: Health check fails
   - Start service: `docker-compose up -d ai-automation-service`
   - Wait for health: `curl http://localhost:8024/health`

## Improvement Process

When improvements are identified:

1. **Analysis**: Script analyzes scores and identifies issues
2. **Plan**: Creates `IMPROVEMENT_PLAN.md` with:
   - Issues identified
   - Files to modify
   - Proposed actions
3. **Deployment**: Automatically rebuilds and restarts service
4. **Next Cycle**: Continues with updated service

## Manual Intervention

If the script stops for errors:

1. Review the error report in `cycle-{N}/ERROR_REPORT.md`
2. Fix the issue in the code
3. Deploy: `docker-compose build ai-automation-service && docker-compose restart ai-automation-service`
4. Re-run the script (it will continue from where it stopped)

## Summary Report

After all cycles complete, `SUMMARY.md` contains:

- Cycle-by-cycle results
- Improvement trends
- Final automation YAML
- Key learnings
- Remaining issues

## Configuration

Edit the script to modify:

- `BASE_URL`: API endpoint (default: `http://localhost:8024/api/v1/ask-ai`)
- `TARGET_PROMPT`: Test prompt to use
- `MAX_CYCLES`: Number of cycles (default: 5)
- `TIMEOUT`: API timeout in seconds (default: 300)
- `OUTPUT_DIR`: Output directory (default: `implementation/continuous-improvement`)

## Troubleshooting

### Service Not Healthy
```bash
# Check service status
docker-compose ps ai-automation-service

# Check logs
docker-compose logs ai-automation-service

# Restart service
docker-compose restart ai-automation-service
```

### API Timeout
- Increase `TIMEOUT` in script
- Check service performance
- Review OpenAI API response times

### Clarification Questions Not Answered
- Review `clarification_rounds.json` to see questions
- Improve `ClarificationHandler.answer_question()` logic
- Add more context matching rules

## Notes

- The script automatically answers clarification questions based on prompt context
- Service deployment is automatic when improvements are identified
- All data is saved for analysis and debugging
- The script stops on critical errors for manual review

