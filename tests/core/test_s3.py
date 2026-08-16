from unittest.mock import MagicMock


def test_generate_presigned_upload_url_returns_url():
    from app.core.s3 import generate_presigned_upload_url, settings

    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    url = generate_presigned_upload_url(
        mock_client,
        key="profiles/children/abc/def.jpg",
        content_type="image/jpeg",
    )

    mock_client.generate_presigned_url.assert_called_once_with(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": "profiles/children/abc/def.jpg",
            "ContentType": "image/jpeg",
        },
        ExpiresIn=300,
    )
    assert url == "https://s3.example.com/presigned"


def test_generate_presigned_upload_url_uses_custom_expires():
    from app.core.s3 import generate_presigned_upload_url

    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    generate_presigned_upload_url(
        mock_client,
        key="profiles/children/abc/def.jpg",
        content_type="image/png",
        expires=600,
    )

    call_kwargs = mock_client.generate_presigned_url.call_args[1]
    assert call_kwargs["ExpiresIn"] == 600
