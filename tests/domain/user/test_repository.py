import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child
from app.models.parent import Parent


@pytest.fixture
def db():
    return AsyncMock(spec=AsyncSession)


async def test_get_all_by_parent_returns_list(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    parent_id = uuid.uuid4()
    child = Child(id=uuid.uuid4(), parent_id=parent_id, name="지오")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [child]
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_all_by_parent(parent_id)

    assert len(result) == 1
    assert result[0].name == "지오"


async def test_create_adds_child_with_profile_image_url(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    parent_id = uuid.uuid4()
    img_url = "https://example.com/img.jpg"

    result = await repo.create(parent_id, "지오", img_url)

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()
    assert isinstance(result, Child)
    assert result.name == "지오"
    assert result.parent_id == parent_id
    assert result.profile_image_url == img_url


async def test_update_parent_commits_and_refreshes(db):
    from app.domain.user.repository import ParentRepository

    repo = ParentRepository(db)
    parent = Parent(id=uuid.uuid4(), name="홍길동")

    result = await repo.update_parent(parent, "김철수")

    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(parent)
    assert result.name == "김철수"
