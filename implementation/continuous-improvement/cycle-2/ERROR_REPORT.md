# Error Report - Cycle 2

**Timestamp**: 2025-11-23T12:26:03.585624

**Error**: Approval failed: Failed to validate entities in automation YAML (Type: validation_error). Details: Entity validation failed: Scene entities referenced but not created via scene.create: scene.wled_office_pre_burst". All scene entities must be created using the scene.create service before they can be used. Example: Use 'service: scene.create' with 'data.scene_id' before referencing the scene entity.

## Next Steps

1. Review the error message above
2. Check service logs: `docker-compose logs ai-automation-service`
3. Fix the issue in the code
4. Deploy: `docker-compose build ai-automation-service && docker-compose restart ai-automation-service`
5. Re-run this script
