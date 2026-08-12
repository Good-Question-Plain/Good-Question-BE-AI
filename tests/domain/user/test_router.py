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
    svc.update_me = AsyncMock(
        return_value=ParentResponse(id=PARENT_ID, name="김철수", email="test@example.com")
    )
    svc.get_children = AsyncMock(return_value=[])
    svc.create_child = AsyncMock(
        return_value=ChildResponse(
            id=CHILD_ID,
            name="지오",
            profile_image_url="https://example.com/img.jpg",
        )
    )
    return svc


@pytest.fixture
def mock_s3():
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"
    return s3


@pytest.fixture
def client(mock_parent, mock_svc, mock_s3):
    from main import app
    from app.core.dependencies import get_current_user, get_current_user_with_email
    from app.core.s3 import get_s3_client
    from app.domain.user.router import _get_service

    app.dependency_overrides[get_current_user] = lambda: mock_parent
    app.dependency_overrides[get_current_user_with_email] = lambda: (
        mock_parent,
        "test@example.com",
    )
    app.dependency_overrides[_get_service] = lambda: mock_svc
    app.dependency_overrides[get_s3_client] = lambda: mock_s3

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_get_me_returns_200_with_parent_info(client):
    resp = client.get("/users/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "홍길동"
    assert body["email"] == "test@example.com"


def test_update_me_returns_200_with_updated_name(client):
    resp = client.patch("/users/me", json={"name": "김철수"})

    assert resp.status_code == 200
    assert resp.json()["name"] == "김철수"


def test_update_me_returns_400_for_empty_name(client):
    resp = client.patch("/users/me", json={"name": ""})

    assert resp.status_code == 400


def test_update_me_returns_400_for_whitespace_name(client):
    resp = client.patch("/users/me", json={"name": "   "})

    assert resp.status_code == 400


def test_get_children_returns_200_with_empty_list(client):
    resp = client.get("/users/me/children")

    assert resp.status_code == 200
    assert resp.json() == []


def test_create_child_returns_201_with_profile_image_url(client):
    resp = client.post(
        "/users/me/children",
        json={"name": "지오", "profile_image_url": "https://example.com/img.jpg"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "지오"
    assert body["profile_image_url"] == "https://example.com/img.jpg"


def test_create_child_returns_422_without_profile_image_url(client):
    resp = client.post("/users/me/children", json={"name": "지오"})

    assert resp.status_code == 422


def test_get_presigned_url_returns_200_with_url_and_key(client):
    resp = client.post(
        "/users/profile-image/presigned-url",
        json={"content_type": "image/jpeg"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "upload_url" in body
    assert "object_key" in body
    assert body["object_key"].startswith(f"profiles/children/{PARENT_ID}/")
    assert body["object_key"].endswith(".jpeg")


def test_get_presigned_url_returns_400_for_non_image(client):
    resp = client.post(
        "/users/profile-image/presigned-url",
        json={"content_type": "application/pdf"},
    )

    assert resp.status_code == 400
