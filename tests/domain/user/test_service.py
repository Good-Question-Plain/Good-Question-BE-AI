import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.child import Child
from app.models.parent import Parent


@pytest.fixture
def parent():
    return Parent(id=uuid.uuid4(), name="홍길동")


@pytest.fixture
def service():
    from app.domain.user.service import UserService

    svc = UserService(AsyncMock())
    svc.repo = MagicMock()
    return svc


def test_get_me_returns_parent_response(service, parent):
    result = service.get_me(parent, "test@example.com")

    assert result.id == parent.id
    assert result.name == "홍길동"
    assert result.email == "test@example.com"


async def test_get_children_returns_mapped_list(service, parent):
    child = Child(id=uuid.uuid4(), parent_id=parent.id, name="지오")
    service.repo.get_all_by_parent = AsyncMock(return_value=[child])

    result = await service.get_children(parent)

    assert len(result) == 1
    assert result[0].name == "지오"


async def test_create_child_returns_created(service, parent):
    from app.domain.user.schema import ChildCreateRequest

    child = Child(id=uuid.uuid4(), parent_id=parent.id, name="지오")
    service.repo.create = AsyncMock(return_value=child)

    result = await service.create_child(parent, ChildCreateRequest(name="지오"))

    service.repo.create.assert_awaited_once_with(parent.id, "지오")
    assert result.name == "지오"
