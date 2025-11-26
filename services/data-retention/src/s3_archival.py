"""
S3 Archival Manager
Handles long-term archival to AWS S3 Glacier

NOTE: This module requires InfluxDB 3.0+ with SQL support.
For InfluxDB 2.7, these operations are disabled to prevent SSL errors.
"""

import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

# Try to import InfluxDB 3.0 client, but don't fail if not available
try:
    from influxdb_client_3 import InfluxDBClient3, Point
    INFLUXDB3_AVAILABLE = True
except ImportError:
    INFLUXDB3_AVAILABLE = False
    InfluxDBClient3 = None
    Point = None


class S3ArchivalManager:
    """Manage S3 archival for long-term data retention"""

    def __init__(self):
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')

        # S3 configuration
        self.s3_bucket = os.getenv('S3_ARCHIVE_BUCKET', '')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')

        self.influxdb_client = None
        self.s3_client = None
        self.enabled = False

        # Only initialize S3 if configured
        if self.s3_bucket:
            self.s3_client = boto3.client(
                's3',
                region_name=self.aws_region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )

    def initialize(self):
        """Initialize InfluxDB client - disabled for InfluxDB 2.7"""
        if not INFLUXDB3_AVAILABLE:
            logger.warning("InfluxDB 3.0 client not available. S3 archival disabled (requires InfluxDB 3.0+ with SQL support).")
            self.enabled = False
            return
        
        # Check if we're using InfluxDB 2.7 (HTTP) vs 3.0 (gRPC)
        if self.influxdb_url.startswith('http://') or self.influxdb_url.startswith('https://'):
            logger.warning("S3 archival requires InfluxDB 3.0+ with gRPC. InfluxDB 2.7 detected - feature disabled.")
            self.enabled = False
            return
        
        try:
            self.influxdb_client = InfluxDBClient3(
                host=self.influxdb_url,
                token=self.influxdb_token,
                database=self.influxdb_bucket,
                org=self.influxdb_org
            )
            self.enabled = True
            logger.info("S3 archival manager initialized with InfluxDB 3.0")
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB 3.0 client: {e}")
            self.enabled = False

    async def archive_to_s3(self) -> dict[str, Any]:
        """Archive 365+ day old daily aggregates to S3"""

        if not self.enabled:
            logger.debug("S3 archival disabled - skipping archival")
            return {'status': 'disabled', 'reason': 'InfluxDB 3.0+ required'}

        if not self.s3_bucket or not self.s3_client:
            logger.warning("S3 not configured, skipping archival")
            return {'status': 'skipped', 'reason': 's3_not_configured'}

        logger.info("Starting S3 archival...")

        cutoff_date = datetime.now() - timedelta(days=365)

        try:
            # Query old data
            query = f'''
            SELECT * FROM daily_aggregates
            WHERE time < TIMESTAMP '{cutoff_date.isoformat()}'
            ORDER BY time
            '''

            result = self.influxdb_client.query(query, language='sql', mode='pandas')

            if result.empty:
                logger.info("No data to archive")
                return {'status': 'no_data'}

            # Convert to Arrow table
            table = pa.Table.from_pandas(result)

            # Save to Parquet file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.parquet') as f:
                parquet_file = f.name
                pq.write_table(table, f, compression='gzip')

            file_size_mb = os.path.getsize(parquet_file) / (1024 * 1024)

            # Upload to S3
            s3_key = f"archives/{cutoff_date.year}/data_{cutoff_date.strftime('%Y%m%d')}.parquet"

            self.s3_client.upload_file(
                Filename=parquet_file,
                Bucket=self.s3_bucket,
                Key=s3_key,
                ExtraArgs={
                    'StorageClass': 'GLACIER_IR',
                    'ServerSideEncryption': 'AES256'
                }
            )

            # Store archive metadata in InfluxDB
            metadata_point = Point("archive_metadata") \
                .tag("s3_key", s3_key) \
                .field("start_date", cutoff_date.isoformat()) \
                .field("record_count", len(result)) \
                .field("file_size_mb", file_size_mb) \
                .time(datetime.now())

            self.influxdb_client.write(metadata_point)

            # Clean up temp file
            os.remove(parquet_file)

            logger.info(f"Archived {len(result)} records to s3://{self.s3_bucket}/{s3_key} ({file_size_mb:.2f}MB)")

            return {
                'status': 'success',
                's3_key': s3_key,
                'records_archived': len(result),
                'file_size_mb': file_size_mb,
                'cutoff_date': cutoff_date.isoformat(),
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error archiving to S3: {e}")
            return {'status': 'error', 'error': str(e)}

    async def restore_from_s3(self, s3_key: str) -> pd.DataFrame:
        """Restore data from S3 archive"""

        if not self.s3_client:
            raise Exception("S3 not configured")

        logger.info(f"Restoring from S3: {s3_key}")

        try:
            # Download from S3
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as f:
                local_file = f.name

                self.s3_client.download_file(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Filename=local_file
                )

            # Read Parquet file
            table = pq.read_table(local_file)
            df = table.to_pandas()

            # Clean up
            os.remove(local_file)

            logger.info(f"Restored {len(df)} records from S3")

            return df

        except Exception as e:
            logger.error(f"Error restoring from S3: {e}")
            raise

