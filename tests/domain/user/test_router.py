import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import NotFoundError
from app.models.parent import Parent

PARENT_ID = uuid.uuid4()
CHILD_ID = uuid.uuid4()


@pytest.fixture
def mock_parent():
    return Parent(id=PARENT_ID, name="홍길동")


@pytest.fixture
def mock_svc():
    from app.domain.user.schema import ChildResponse, ParentResponse

    svc = MagicMock()
    svc.get_me = MagicMock(
        return_value=ParentResponse(id=PARENT_ID, name="홍길동", email="test@example.com")
    )
    svc.get_children = AsyncMock(return_value=[])
    svc.create_child = AsyncMock(
        return_value=ChildResponse(id=CHILD_ID, name="지오", birth_year=2018)
    )
    svc.update_child = AsyncMock(
        return_value=ChildResponse(id=CHILD_ID, name="수정", birth_year=2018)
    )
    svc.delete_child = AsyncMock()
    return svc


@pytest.fixture
def client(mock_parent, mock_svc):
    from main import app
    from app.core.dependencies import get_current_user, get_current_user_with_email
    from app.domain.user.router import _get_service

    app.dependency_overrides[get_current_user] = lambda: mock_parent
    app.dependency_overrides[get_current_user_with_email] = lambda: (mock_parent, "test@example.com")
    app.dependency_overrides[_get_service] = lambda: mock_svc

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_get_me_returns_200_with_parent_info(client):
    resp = client.get("/users/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "홍길동"
    assert body["email"] == "test@example.com"


def test_get_children_returns_200_with_empty_list(client):
    resp = client.get("/users/me/children")

    assert resp.status_code == 200
    assert resp.json() == []


def test_create_child_returns_201(client):
    resp = client.post("/users/me/children", json={"name": "지오", "birth_year": 2018})

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "지오"
    assert body["birth_year"] == 2018


def test_update_child_returns_200(client):
    resp = client.patch(f"/users/me/children/{CHILD_ID}", json={"name": "수정"})

    assert resp.status_code == 200
    assert resp.json()["name"] == "수정"


def test_delete_child_returns_200_with_message(client):
    resp = client.delete(f"/users/me/children/{CHILD_ID}")

    assert resp.status_code == 200
    assert resp.json()["message"] == "자녀 프로필이 삭제되었습니다."


def test_update_child_not_found_returns_404(client, mock_svc):
    mock_svc.update_child = AsyncMock(
        side_effect=NotFoundError("자녀 프로필을 찾을 수 없습니다.")
    )

    resp = client.patch(f"/users/me/children/{uuid.uuid4()}", json={"name": "없는아이"})

    assert resp.status_code == 404


def test_delete_child_not_found_returns_404(client, mock_svc):
    mock_svc.delete_child = AsyncMock(
        side_effect=NotFoundError("자녀 프로필을 찾을 수 없습니다.")
    )

    resp = client.delete(f"/users/me/children/{uuid.uuid4()}")

    assert resp.status_code == 404
