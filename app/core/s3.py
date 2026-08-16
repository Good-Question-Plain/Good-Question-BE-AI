import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError

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


def get_public_url(key: str) -> str:
    return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


async def check_object_exists(client: Any, key: str) -> bool:
    try:
        await asyncio.to_thread(
            client.head_object, Bucket=settings.AWS_S3_BUCKET, Key=key
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            return False
        raise


def resolve_image_url(key: str | None) -> str | None:
    """object key → 공개 URL 변환. None이거나 이미 URL이면 그대로 반환."""
    if key is None or key.startswith("http"):
        return key
    return get_public_url(key)
