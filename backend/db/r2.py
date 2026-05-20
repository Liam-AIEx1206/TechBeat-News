"""Cloudflare R2 upload helper (S3-compatible API)."""
import os
import boto3
from botocore.config import Config
from pathlib import Path


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_to_r2(local_path: Path, key: str, content_type: str = "application/octet-stream") -> str:
    """Upload file to R2 and return public URL. Returns empty string if R2 not configured."""
    account_id = os.getenv("R2_ACCOUNT_ID")
    bucket     = os.getenv("R2_BUCKET")
    public_url = os.getenv("R2_PUBLIC_URL", "")

    if not all([account_id, bucket, os.getenv("R2_ACCESS_KEY_ID"), os.getenv("R2_SECRET_ACCESS_KEY")]):
        return ""  # R2 not configured — skip upload

    try:
        client = get_r2_client()
        with open(local_path, "rb") as f:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=f,
                ContentType=content_type,
            )
        return f"{public_url.rstrip('/')}/{key}"
    except Exception as e:
        print(f"[R2] Upload failed for {key}: {e}")
        return ""
