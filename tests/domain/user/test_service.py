import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError
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
    child = Child(id=uuid.uuid4(), parent_id=parent.id, name="지오", birth_year=2018)
    service.repo.get_all_by_parent = AsyncMock(return_value=[child])

    result = await service.get_children(parent)

    assert len(result) == 1
    assert result[0].name == "지오"
    assert result[0].birth_year == 2018


async def test_create_child_returns_created(service, parent):
    from app.domain.user.schema import ChildCreateRequest

    child = Child(id=uuid.uuid4(), parent_id=parent.id, name="지오", birth_year=2018)
    service.repo.create = AsyncMock(return_value=child)

    result = await service.create_child(parent, ChildCreateRequest(name="지오", birth_year=2018))

    service.repo.create.assert_awaited_once_with(parent.id, "지오", 2018)
    assert result.name == "지오"


async def test_update_child_raises_not_found_when_missing(service, parent):
    from app.domain.user.schema import ChildUpdateRequest

    service.repo.get_by_id_and_parent = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.update_child(parent, uuid.uuid4(), ChildUpdateRequest(name="수정"))


async def test_update_child_success(service, parent):
    from app.domain.user.schema import ChildUpdateRequest

    child = Child(id=uuid.uuid4(), parent_id=parent.id, name="지오", birth_year=2018)
    updated = Child(id=child.id, parent_id=parent.id, name="수정", birth_year=2018)
    service.repo.get_by_id_and_parent = AsyncMock(return_value=child)
    service.repo.update = AsyncMock(return_value=updated)

    result = await service.update_child(parent, child.id, ChildUpdateRequest(name="수정"))

    assert result.name == "수정"


async def test_delete_child_raises_not_found_when_missing(service, parent):
    service.repo.get_by_id_and_parent = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.delete_child(parent, uuid.uuid4())


async def test_delete_child_calls_repo_delete(service, parent):
    child = Child(id=uuid.uuid4(), parent_id=parent.id, name="지오", birth_year=2018)
    service.repo.get_by_id_and_parent = AsyncMock(return_value=child)
    service.repo.delete = AsyncMock()

    await service.delete_child(parent, child.id)

    service.repo.delete.assert_awaited_once_with(child)
