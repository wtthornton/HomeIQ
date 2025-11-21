# Data Retention Service

**Port:** 8080
**Technology:** Python 3.11+, FastAPI 0.121, InfluxDB 3.0
**Container:** `homeiq-data-retention`
**Status:** Production Ready

The Data Retention Service is a comprehensive solution for managing data lifecycle, storage optimization, and backup operations in the HomeIQ system for single NUC deployment.

## Overview

This service provides:
- **Data Retention Policies**: Configurable policies for automatic data cleanup
- **Storage Monitoring**: Real-time monitoring of storage usage and alerts
- **Data Compression**: Automatic compression of historical data
- **Backup & Restore**: Automated backup creation and restoration capabilities
- **Cleanup Operations**: Manual and scheduled data cleanup

## API Endpoints

The service exposes a REST API on port 8080 with the following endpoints:

### Health & Statistics

#### `GET /health`
Returns the current health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "cleanup_service": true,
    "storage_monitor": true,
    "compression_service": true,
    "backup_service": true
  },
  "policy_count": 5
}
```

#### `GET /stats`
Returns comprehensive service statistics.

**Response:**
```json
{
  "service_status": {
    "cleanup_service": true,
    "storage_monitor": true,
    "compression_service": true,
    "backup_service": true,
    "policy_count": 5
  },
  "policy_statistics": {
    "total_policies": 5,
    "enabled_policies": 4,
    "disabled_policies": 1
  },
  "cleanup_statistics": {
    "last_cleanup": "2024-01-01T12:00:00Z",
    "records_cleaned": 1000,
    "space_freed_mb": 50.5
  },
  "storage_statistics": {
    "total_space_gb": 1000,
    "used_space_gb": 750,
    "available_space_gb": 250,
    "usage_percentage": 75.0
  },
  "compression_statistics": {
    "compression_ratio": 0.3,
    "space_saved_mb": 200.0,
    "last_compression": "2024-01-01T12:00:00Z"
  },
  "backup_statistics": {
    "total_backups": 10,
    "total_size_gb": 5.2,
    "last_backup": "2024-01-01T12:00:00Z"
  }
}
```

### Policy Management

#### `GET /policies`
Returns all configured retention policies.

**Response:**
```json
[
  {
    "name": "sensor_data_retention",
    "description": "Retain sensor data for 30 days",
    "retention_period": 30,
    "retention_unit": "days",
    "enabled": true,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
]
```

#### `POST /policies`
Creates a new retention policy.

**Request Body:**
```json
{
  "name": "event_data_retention",
  "description": "Retain event data for 7 days",
  "retention_period": 7,
  "retention_unit": "days",
  "enabled": true
}
```

**Response:**
```json
{
  "message": "Policy created successfully",
  "policy": {
    "name": "event_data_retention",
    "description": "Retain event data for 7 days",
    "retention_period": 7,
    "retention_unit": "days",
    "enabled": true,
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### `PUT /policies`
Updates an existing retention policy.

**Request Body:**
```json
{
  "name": "sensor_data_retention",
  "description": "Retain sensor data for 60 days",
  "retention_period": 60,
  "retention_unit": "days",
  "enabled": true
}
```

**Response:**
```json
{
  "message": "Policy updated successfully",
  "policy": {
    "name": "sensor_data_retention",
    "description": "Retain sensor data for 60 days",
    "retention_period": 60,
    "retention_unit": "days",
    "enabled": true,
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

#### `DELETE /policies/{policy_name}`
Deletes a retention policy.

**Response:**
```json
{
  "message": "Policy deleted successfully",
  "policy_name": "old_policy"
}
```

### Cleanup Operations

#### `POST /cleanup`
Manually triggers data cleanup.

**Request Body (optional):**
```json
{
  "policy_name": "sensor_data_retention"
}
```

**Response:**
```json
{
  "message": "Cleanup completed successfully",
  "results": [
    {
      "policy_name": "sensor_data_retention",
      "records_processed": 1000,
      "records_deleted": 500,
      "space_freed_mb": 25.5,
      "execution_time_seconds": 30.2
    }
  ]
}
```

### Backup Operations

#### `POST /backup`
Creates a new backup.

**Request Body:**
```json
{
  "backup_type": "full",
  "include_data": true,
  "include_config": true,
  "include_logs": false
}
```

**Response:**
```json
{
  "message": "Backup created successfully",
  "backup": {
    "id": "backup_20240101_120000",
    "type": "full",
    "size_mb": 150.5,
    "created_at": "2024-01-01T12:00:00Z",
    "includes": {
      "data": true,
      "config": true,
      "logs": false
    }
  }
}
```

#### `POST /restore`
Restores from a backup.

**Request Body:**
```json
{
  "backup_id": "backup_20240101_120000",
  "restore_data": true,
  "restore_config": true,
  "restore_logs": false
}
```

**Response:**
```json
{
  "message": "Restore completed successfully",
  "backup_id": "backup_20240101_120000",
  "restored_components": ["data", "config"]
}
```

#### `GET /backups`
Returns backup history.

**Query Parameters:**
- `limit` (optional): Maximum number of backups to return (default: 100)

**Response:**
```json
[
  {
    "id": "backup_20240101_120000",
    "type": "full",
    "size_mb": 150.5,
    "created_at": "2024-01-01T12:00:00Z",
    "status": "completed",
    "includes": {
      "data": true,
      "config": true,
      "logs": false
    }
  }
]
```

#### `GET /backup-stats`
Returns backup statistics.

**Response:**
```json
{
  "total_backups": 10,
  "total_size_gb": 5.2,
  "average_size_mb": 520.0,
  "last_backup": "2024-01-01T12:00:00Z",
  "successful_backups": 9,
  "failed_backups": 1,
  "backup_frequency_hours": 24
}
```

#### `DELETE /backups/cleanup`
Cleans up old backup files.

**Query Parameters:**
- `days_to_keep` (optional): Number of days to keep backups (default: 30)

**Response:**
```json
{
  "message": "Backup cleanup completed",
  "backups_deleted": 5,
  "space_freed_mb": 250.0
}
```

## Configuration

The service can be configured using environment variables:

### Service Configuration
- `PORT`: Service port (default: 8080)
- `CLEANUP_INTERVAL_HOURS`: Cleanup interval in hours (default: 24)
- `MONITORING_INTERVAL_MINUTES`: Storage monitoring interval in minutes (default: 5)
- `COMPRESSION_INTERVAL_HOURS`: Compression interval in hours (default: 24)
- `BACKUP_INTERVAL_HOURS`: Backup interval in hours (default: 24)
- `BACKUP_DIR`: Backup directory path (default: /backups)

### Database Configuration
- `INFLUXDB_HOST`: InfluxDB host
- `INFLUXDB_PORT`: InfluxDB port
- `INFLUXDB_DATABASE`: InfluxDB database name
- `INFLUXDB_USERNAME`: InfluxDB username
- `INFLUXDB_PASSWORD`: InfluxDB password

## Usage Examples

### Creating a Retention Policy
```bash
curl -X POST http://localhost:8080/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sensor_data_retention",
    "description": "Retain sensor data for 30 days",
    "retention_period": 30,
    "retention_unit": "days",
    "enabled": true
  }'
```

### Running Manual Cleanup
```bash
curl -X POST http://localhost:8080/cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "policy_name": "sensor_data_retention"
  }'
```

### Creating a Backup
```bash
curl -X POST http://localhost:8080/backup \
  -H "Content-Type: application/json" \
  -d '{
    "backup_type": "full",
    "include_data": true,
    "include_config": true,
    "include_logs": false
  }'
```

### Checking Service Health
```bash
curl http://localhost:8080/health
```

### Getting Service Statistics
```bash
curl http://localhost:8080/stats
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a message and optional details:

```json
{
  "error": "Policy not found",
  "message": "The specified policy 'invalid_policy' does not exist",
  "code": "POLICY_NOT_FOUND"
}
```

## Monitoring

The service provides comprehensive monitoring capabilities:

- **Health Checks**: Regular health status monitoring
- **Storage Alerts**: Automatic alerts for storage thresholds
- **Performance Metrics**: Cleanup and compression performance tracking
- **Backup Monitoring**: Backup success/failure tracking

## Security

- All API endpoints require proper authentication
- Sensitive operations (backup, restore, cleanup) are logged
- Backup files are encrypted and stored securely
- Access to backup files is restricted

## Troubleshooting

### Common Issues

1. **Service won't start**
   - Check port availability
   - Verify database connectivity
   - Check environment variables

2. **Cleanup not working**
   - Verify retention policies are enabled
   - Check database permissions
   - Review cleanup logs

3. **Backup failures**
   - Check backup directory permissions
   - Verify available disk space
   - Review backup service logs

### Logs

Service logs are available via Docker logs:
```bash
docker logs data-retention-service
```

## Development

### Running Locally
```bash
cd services/data-retention
python -m src.main
```

### Running Tests
```bash
cd services/data-retention
python -m pytest tests/
```

### Building Docker Image
```bash
docker build -t data-retention-service .
```

## License

This service is part of the Home Assistant Ingestor project and follows the same license terms.

## Version History

### 2.1 (November 15, 2025)
- Documentation verified for 2025 standards
- Comprehensive API endpoint documentation
- Backup and restore workflows documented
- Storage monitoring and alerts

### 2.0 (Initial Production Release)
- Data retention policies
- Storage monitoring
- Data compression
- Backup & restore operations
- Cleanup automation

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8080
