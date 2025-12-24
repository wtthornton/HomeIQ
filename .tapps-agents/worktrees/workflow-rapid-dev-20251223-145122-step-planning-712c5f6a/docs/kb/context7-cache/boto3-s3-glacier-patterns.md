# boto3 S3 and Glacier Patterns
**Context7 KB Cache**

**Library:** boto3 (/websites/boto3_amazonaws_v1_api)  
**Topic:** S3 upload, download, Glacier storage class  
**Retrieved:** October 10, 2025  
**Code Snippets:** 107,133 available  
**Trust Score:** 7.5

---

## S3 Upload with Storage Class

### Upload Object with Glacier Instant Retrieval

```python
import boto3

s3_client = boto3.client('s3')

response = s3_client.put_object(
    Bucket='my-archive-bucket',
    Key='archives/2025/data_20251010.parquet',
    Body=open('data.parquet', 'rb'),
    StorageClass='GLACIER_IR',  # Glacier Instant Retrieval
    ServerSideEncryption='AES256'
)

print(response)
```

**Storage Classes:**
- `STANDARD` - Default, frequently accessed
- `STANDARD_IA` - Infrequent access, cheaper
- `GLACIER_IR` - Instant retrieval, long-term archival ($0.004/GB/month)
- `GLACIER` - 3-5 hour retrieval, cheapest long-term
- `DEEP_ARCHIVE` - 12-48 hour retrieval, lowest cost

---

## Multipart Upload for Large Files

### Initiate Multipart Upload

```python
response = s3_client.create_multipart_upload(
    Bucket='my-bucket',
    Key='large-archive.parquet',
    StorageClass='GLACIER_IR'
)

upload_id = response['UploadId']
```

### Upload Parts

```python
parts = []
part_number = 1
chunk_size = 5 * 1024 * 1024  # 5MB chunks

with open('large-file.parquet', 'rb') as f:
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        
        part = s3_client.upload_part(
            Bucket='my-bucket',
            Key='large-archive.parquet',
            PartNumber=part_number,
            UploadId=upload_id,
            Body=data
        )
        
        parts.append({
            'PartNumber': part_number,
            'ETag': part['ETag']
        })
        
        part_number += 1
```

### Complete Multipart Upload

```python
s3_client.complete_multipart_upload(
    Bucket='my-bucket',
    Key='large-archive.parquet',
    UploadId=upload_id,
    MultipartUpload={'Parts': parts}
)
```

---

## Download from S3

```python
s3_client.download_file(
    Bucket='my-archive-bucket',
    Key='archives/2025/data_20251010.parquet',
    Filename='/tmp/restored_data.parquet'
)
```

---

## Patterns for HA Ingestor

### Simple Archival Pattern

```python
import boto3
import os

class S3ArchivalService:
    """Simple S3 archival for HA Ingestor"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket = os.getenv('S3_ARCHIVE_BUCKET')
    
    async def archive_file(self, local_path: str, s3_key: str):
        """Upload file to S3 Glacier IR"""
        
        self.s3_client.upload_file(
            Filename=local_path,
            Bucket=self.bucket,
            Key=s3_key,
            ExtraArgs={
                'StorageClass': 'GLACIER_IR',
                'ServerSideEncryption': 'AES256'
            }
        )
        
        print(f"Archived {local_path} to s3://{self.bucket}/{s3_key}")
    
    async def restore_file(self, s3_key: str, local_path: str):
        """Download file from S3"""
        
        self.s3_client.download_file(
            Bucket=self.bucket,
            Key=s3_key,
            Filename=local_path
        )
        
        print(f"Restored s3://{self.bucket}/{s3_key} to {local_path}")
    
    def get_file_size(self, s3_key: str) -> int:
        """Get file size in bytes"""
        
        response = self.s3_client.head_object(
            Bucket=self.bucket,
            Key=s3_key
        )
        
        return response['ContentLength']
```

---

## Cost Optimization

**Glacier Instant Retrieval Pricing (as of 2025):**
- Storage: $0.004/GB/month
- PUT requests: $0.02 per 1,000 requests
- GET requests: $0.01 per 1,000 requests
- Retrieval: $0.03/GB (instant)

**Example Cost for HA Ingestor:**
- 5 years of daily aggregates: ~20 GB
- Monthly cost: 20 GB × $0.004 = $0.08/month = $0.96/year
- Upload cost: 365 files/year × $0.02/1000 = $0.007/year
- **Total: ~$1/year for 5 years of data**

---

**Source:** Context7 via /websites/boto3_amazonaws_v1_api  
**Usage:** S3 archival in data-retention service  
**Cached:** 2025-10-10

