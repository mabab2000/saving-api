import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import HTTPException, status

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "saving-api-photos")

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(file_content: bytes, file_name: str, content_type: str) -> str:
    """
    Upload file to S3 and return the S3 key (file path)
    """
    try:
        # Upload file to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=file_name,
            Body=file_content,
            ContentType=content_type
        )
        
        # Return the S3 key (we'll generate pre-signed URLs when needed)
        return file_name
        
    except NoCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS credentials not found"
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading to S3: {str(e)}"
        )

def generate_presigned_url(s3_key: str, expiration: int = 604800) -> str:
    """
    Generate a pre-signed URL for accessing an S3 object
    Default expiration: 604800 seconds = 7 days
    """
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return response
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating pre-signed URL: {str(e)}"
        )