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
    svc.parent_repo = MagicMock()
    return svc


def test_get_me_returns_parent_response(service, parent):
    result = service.get_me(parent, "test@example.com")

    assert result.id == parent.id
    assert result.name == "홍길동"
    assert result.email == "test@example.com"


async def test_get_children_returns_mapped_list(service, parent):
    child = Child(
        id=uuid.uuid4(),
        parent_id=parent.id,
        name="지오",
        profile_image_url="https://example.com/img.jpg",
    )
    service.repo.get_all_by_parent = AsyncMock(return_value=[child])

    result = await service.get_children(parent)

    assert len(result) == 1
    assert result[0].name == "지오"
    assert result[0].profile_image_url == "https://example.com/img.jpg"


async def test_create_child_passes_profile_image_url(service, parent):
    from app.domain.user.schema import ChildCreateRequest

    child = Child(
        id=uuid.uuid4(),
        parent_id=parent.id,
        name="지오",
        profile_image_url="https://example.com/img.jpg",
    )
    service.repo.create = AsyncMock(return_value=child)

    result = await service.create_child(
        parent,
        ChildCreateRequest(name="지오", profile_image_url="https://example.com/img.jpg"),
    )

    service.repo.create.assert_awaited_once_with(
        parent.id, "지오", "https://example.com/img.jpg"
    )
    assert result.profile_image_url == "https://example.com/img.jpg"


async def test_update_me_returns_updated_parent_response(service, parent):
    from app.domain.user.schema import ParentUpdateRequest

    updated_parent = Parent(id=parent.id, name="김철수")
    service.parent_repo.update_parent = AsyncMock(return_value=updated_parent)

    result = await service.update_me(
        parent, ParentUpdateRequest(name="김철수"), "test@example.com"
    )

    service.parent_repo.update_parent.assert_awaited_once_with(parent, "김철수")
    assert result.name == "김철수"
    assert result.email == "test@example.com"
