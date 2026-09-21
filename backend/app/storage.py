"""S3-backed original-file storage; local directory adapter for offline development."""
import os
from pathlib import Path

import boto3


def save_source(data: bytes, key: str) -> None:
    bucket = os.getenv("S3_BUCKET")
    if bucket:
        boto3.client("s3").put_object(
            Bucket=bucket, Key=key, Body=data, ContentType="text/csv",
            ServerSideEncryption="AES256",
        )
        return
    root = Path(os.getenv("LOCAL_UPLOAD_DIR", "/tmp/inventory-uploads")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Key is generated from a verified SHA-256 digest, not user input.
    target = root / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
