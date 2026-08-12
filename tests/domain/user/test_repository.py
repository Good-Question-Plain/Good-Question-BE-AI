import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child


@pytest.fixture
def db():
    return AsyncMock(spec=AsyncSession)


async def test_get_all_by_parent_returns_list(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    parent_id = uuid.uuid4()
    child = Child(id=uuid.uuid4(), parent_id=parent_id, name="지오", birth_year=2018)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [child]
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_all_by_parent(parent_id)

    assert len(result) == 1
    assert result[0].name == "지오"


async def test_get_by_id_and_parent_returns_none_when_not_found(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_by_id_and_parent(uuid.uuid4(), uuid.uuid4())

    assert result is None


async def test_create_adds_child_to_db(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    parent_id = uuid.uuid4()

    result = await repo.create(parent_id, "지오", 2018)

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()
    assert isinstance(result, Child)
    assert result.name == "지오"
    assert result.birth_year == 2018
    assert result.parent_id == parent_id


async def test_update_applies_changes(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    child = Child(id=uuid.uuid4(), parent_id=uuid.uuid4(), name="지오", birth_year=2018)

    result = await repo.update(child, name="수정", birth_year=None)

    assert child.name == "수정"
    assert child.birth_year == 2018  # 변경 없음
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_delete_removes_child(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    child = Child(id=uuid.uuid4(), parent_id=uuid.uuid4(), name="지오", birth_year=2018)

    await repo.delete(child)

    db.delete.assert_awaited_once_with(child)
    db.commit.assert_awaited_once()
