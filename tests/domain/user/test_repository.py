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
    child = Child(id=uuid.uuid4(), parent_id=parent_id, name="지오")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [child]
    db.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_all_by_parent(parent_id)

    assert len(result) == 1
    assert result[0].name == "지오"


async def test_create_adds_child_to_db(db):
    from app.domain.user.repository import ChildRepository

    repo = ChildRepository(db)
    parent_id = uuid.uuid4()

    result = await repo.create(parent_id, "지오")

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()
    assert isinstance(result, Child)
    assert result.name == "지오"
    assert result.parent_id == parent_id
