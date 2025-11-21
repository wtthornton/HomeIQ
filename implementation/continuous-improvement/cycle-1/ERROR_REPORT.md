# Error Report - Cycle 1

**Timestamp**: 2025-11-21T09:46:18.840770

**Error**: Approval failed: Automation contains invalid entity IDs (Type: invalid_entities). Details: Invalid entity IDs in YAML: scene.office_wled_before_show

## Next Steps

1. Review the error message above
2. Check service logs: `docker-compose logs ai-automation-service`
3. Fix the issue in the code
4. Deploy: `docker-compose build ai-automation-service && docker-compose restart ai-automation-service`
5. Re-run this script
