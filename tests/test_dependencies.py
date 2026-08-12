import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.exceptions import UnauthorizedError


async def test_get_current_user_with_email_success():
    from app.core.dependencies import get_current_user_with_email
    from app.models.parent import Parent

    parent_id = uuid.uuid4()
    parent = Parent(id=parent_id, name="홍길동")

    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_token"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = parent
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.core.dependencies.verify_supabase_token") as mock_verify:
        mock_verify.return_value = {"sub": str(parent_id), "email": "test@example.com"}
        result_parent, result_email = await get_current_user_with_email(mock_credentials, mock_db)

    assert result_parent == parent
    assert result_email == "test@example.com"


async def test_get_current_user_with_email_no_email_raises_unauthorized():
    from app.core.dependencies import get_current_user_with_email

    mock_credentials = MagicMock()
    mock_credentials.credentials = "token_without_email"
    mock_db = AsyncMock()

    with patch("app.core.dependencies.verify_supabase_token") as mock_verify:
        mock_verify.return_value = {"sub": str(uuid.uuid4())}  # email 없음
        with pytest.raises(UnauthorizedError):
            await get_current_user_with_email(mock_credentials, mock_db)


async def test_get_current_user_with_email_parent_not_found_raises_unauthorized():
    from app.core.dependencies import get_current_user_with_email

    parent_id = uuid.uuid4()
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_token"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.core.dependencies.verify_supabase_token") as mock_verify:
        mock_verify.return_value = {"sub": str(parent_id), "email": "test@example.com"}
        with pytest.raises(UnauthorizedError):
            await get_current_user_with_email(mock_credentials, mock_db)
