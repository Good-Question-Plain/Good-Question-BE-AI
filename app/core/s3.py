from functools import lru_cache
from typing import Any

import boto3

from app.core.config import settings


@lru_cache
def get_s3_client() -> Any:
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def generate_presigned_upload_url(
    client: Any,
    key: str,
    content_type: str,
    expires: int = 300,
) -> str:
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )
