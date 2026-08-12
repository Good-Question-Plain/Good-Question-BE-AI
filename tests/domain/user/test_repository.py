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


async def test_get_by_id_and_parent_returns_child(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()
    child = Child(id=child_id, parent_id=parent_id, name="지오")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = child
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_by_id_and_parent(child_id, parent_id)

    assert result is child


async def test_get_by_id_and_parent_returns_none_when_not_found(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_by_id_and_parent(uuid.uuid4(), uuid.uuid4())

    assert result is None


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


async def test_child_update_commits_non_none_fields(db):
    from app.domain.user.repository import ChildRepository
    from app.domain.user.schema import ChildUpdateRequest

    repo = ChildRepository(db)
    child = Child(id=uuid.uuid4(), parent_id=uuid.uuid4(), name="지오")

    await repo.update(child, ChildUpdateRequest(name="민준", birth_year=2019))

    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(child)
    assert child.name == "민준"
    assert child.birth_year == 2019


async def test_parent_update_commits_non_none_fields(db):
    from app.domain.user.repository import ParentRepository
    from app.domain.user.schema import ParentUpdateRequest

    repo = ParentRepository(db)
    parent = Parent(id=uuid.uuid4(), name="홍길동")

    await repo.update(parent, ParentUpdateRequest(name="김철수"))

    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(parent)
    assert parent.name == "김철수"
