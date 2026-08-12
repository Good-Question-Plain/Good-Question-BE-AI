import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

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
        return_value=ChildResponse(id=CHILD_ID, name="지오")
    )
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
    resp = client.post("/users/me/children", json={"name": "지오"})

    assert resp.status_code == 201
    assert resp.json()["name"] == "지오"
