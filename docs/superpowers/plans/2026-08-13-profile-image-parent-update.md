# 자녀 프로필 이미지 S3 업로드 + 부모 이름 수정 API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자녀 프로필 이미지 S3 Presigned URL 업로드 지원 및 부모 이름 수정 API 추가

**Architecture:** `app/core/s3.py`에 boto3 싱글턴 클라이언트 + Presigned URL 생성 유틸 추가. `PATCH /users/me`는 부모 이름만 수정. `POST /users/profile-image/presigned-url`는 PUT Presigned URL 발급하여 클라이언트가 S3에 직접 업로드. `POST /users/me/children`에 `profile_image_url` 필수 필드 추가.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async (AsyncSession), boto3, pytest-asyncio (asyncio_mode=auto), uv

## Global Constraints

- Python 3.14, FastAPI, SQLAlchemy 2.x async — uv로 의존성 관리 (`uv add boto3`). pip/poetry 사용 금지.
- Supabase JWT 인증 (`CurrentUser` / `CurrentUserWithEmail` dependency)
- 부모는 프로필 이미지 없음 — `Parent` 모델 변경 없음, `POST /auth/sync-profile` 변경 없음
- Presigned URL 유효시간: `expires=300` (5분)
- Object key 형식: `profiles/children/{parent_id}/{uuid4}.{ext}` — parent_id로 경로 격리
- `content_type`이 `image/`로 시작하지 않으면 `BadRequestError` (HTTP 400)
- `PATCH /users/me` name 빈 문자열 또는 공백만인 경우 `BadRequestError` (HTTP 400)
- Migration 번호: **005** (004는 vocabulary tables에서 사용 중)
- 신규 예외 클래스 추가 없음 — 기존 `BadRequestError` (`app.core.exceptions`) 재사용

---

### Task 1: Child 모델 + Migration 005

**Files:**
- Modify: `app/models/child.py`
- Create: `alembic/versions/005_add_profile_image_url_to_children.py`

**Interfaces:**
- Consumes: 없음
- Produces: `Child.profile_image_url: Mapped[str | None]` — Task 3, 4에서 사용

- [ ] **Step 1: Child 모델에 profile_image_url 추가**

`app/models/child.py`의 `name` 필드 다음 줄에 추가:

```python
profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
```

최종 `Child` 클래스 필드 순서 (relationships는 그대로 유지):

```python
class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    parent: Mapped["Parent"] = relationship(back_populates="children")
    consents: Mapped[list["ChildConsent"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )
    story_sessions: Mapped[list["StorySession"]] = relationship(back_populates="child")
    saved_vocabularies: Mapped[list["ChildVocabulary"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: Migration 005 파일 작성**

`alembic/versions/005_add_profile_image_url_to_children.py` 신규 생성:

```python
"""add profile_image_url to children

Revision ID: 005
Revises: 004
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "children",
        sa.Column("profile_image_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("children", "profile_image_url")
```

- [ ] **Step 3: 기존 테스트 통과 확인**

```bash
uv run pytest -v
```

Expected: 전체 PASS (모델 변경은 기존 테스트에 영향 없음 — `profile_image_url`이 nullable이므로)

- [ ] **Step 4: 커밋**

```bash
git add app/models/child.py alembic/versions/005_add_profile_image_url_to_children.py
git commit -m "feat: add profile_image_url to Child model and migration 005"
```

---

### Task 2: S3 클라이언트 모듈

**Files:**
- Create: `app/core/s3.py`
- Modify: `app/core/dependencies.py` — `S3ClientDep` 추가
- Create: `tests/core/__init__.py` (빈 파일)
- Create: `tests/core/test_s3.py`

**Interfaces:**
- Consumes: `settings.AWS_ACCESS_KEY_ID`, `settings.AWS_SECRET_ACCESS_KEY`, `settings.AWS_S3_BUCKET`, `settings.AWS_REGION` (`app.core.config`)
- Produces:
  - `get_s3_client() -> Any` — `@lru_cache` boto3 S3 클라이언트 싱글턴
  - `generate_presigned_upload_url(client: Any, key: str, content_type: str, expires: int = 300) -> str`
  - `S3ClientDep = Annotated[Any, Depends(get_s3_client)]` (dependencies.py)

- [ ] **Step 1: boto3 의존성 추가**

```bash
uv add boto3
```

- [ ] **Step 2: 테스트 디렉터리 생성**

```bash
mkdir -p tests/core && touch tests/core/__init__.py
```

- [ ] **Step 3: 테스트 파일 작성**

`tests/core/test_s3.py` 신규 생성:

```python
from unittest.mock import MagicMock


def test_generate_presigned_upload_url_returns_url():
    from app.core.s3 import generate_presigned_upload_url, settings

    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    url = generate_presigned_upload_url(
        mock_client,
        key="profiles/children/abc/def.jpg",
        content_type="image/jpeg",
    )

    mock_client.generate_presigned_url.assert_called_once_with(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": "profiles/children/abc/def.jpg",
            "ContentType": "image/jpeg",
        },
        ExpiresIn=300,
    )
    assert url == "https://s3.example.com/presigned"


def test_generate_presigned_upload_url_uses_custom_expires():
    from app.core.s3 import generate_presigned_upload_url

    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    generate_presigned_upload_url(
        mock_client,
        key="profiles/children/abc/def.jpg",
        content_type="image/png",
        expires=600,
    )

    call_kwargs = mock_client.generate_presigned_url.call_args[1]
    assert call_kwargs["ExpiresIn"] == 600
```

- [ ] **Step 4: 테스트 실패 확인**

```bash
uv run pytest tests/core/test_s3.py -v
```

Expected: `ModuleNotFoundError` 또는 `ImportError` (`app/core/s3.py` 없으므로)

- [ ] **Step 5: s3.py 구현**

`app/core/s3.py` 신규 생성:

```python
from functools import lru_cache
from typing import Any

import boto3

from app.core.config import settings


@lru_cache
def get_s3_client() -> Any:
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def generate_presigned_upload_url(
    client: Any,
    key: str,
    content_type: str,
    expires: int = 300,
) -> str:
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )
```

- [ ] **Step 6: S3ClientDep를 dependencies.py에 추가**

`app/core/dependencies.py`의 기존 `from typing import Annotated` 줄을 아래로 교체:

```python
from typing import Annotated, Any
```

같은 파일의 `from app.core.redis import get_redis` 줄 바로 아래에 추가:

```python
from app.core.s3 import get_s3_client
```

파일 맨 아래 기존 `CurrentUserWithEmail = ...` 줄 다음에 추가:

```python
S3ClientDep = Annotated[Any, Depends(get_s3_client)]
```

- [ ] **Step 7: 테스트 통과 확인**

```bash
uv run pytest tests/core/test_s3.py -v
```

Expected: 2 PASS

- [ ] **Step 8: 전체 테스트 통과 확인**

```bash
uv run pytest -v
```

Expected: 전체 PASS

- [ ] **Step 9: 커밋**

```bash
git add app/core/s3.py app/core/dependencies.py tests/core/__init__.py tests/core/test_s3.py
git commit -m "feat: add S3 client module and S3ClientDep"
```

---

### Task 3: Schema + Repository + Service 업데이트

**Files:**
- Modify: `app/domain/user/schema.py`
- Modify: `app/domain/user/repository.py`
- Modify: `app/domain/user/service.py`
- Modify: `tests/domain/user/test_service.py`
- Modify: `tests/domain/user/test_repository.py`

**Interfaces:**
- Consumes: `Child.profile_image_url` (Task 1), `settings` (config)
- Produces:
  - `ParentUpdateRequest(name: str)`
  - `ChildCreateRequest(name: str, profile_image_url: str)` — profile_image_url **필수**
  - `ChildResponse(id: uuid.UUID, name: str, profile_image_url: str | None = None)`
  - `PresignedUrlRequest(content_type: str)` — Task 4에서 라우터가 사용
  - `PresignedUrlResponse(upload_url: str, object_key: str)` — Task 4에서 라우터가 사용
  - `ParentRepository.update_parent(parent: Parent, name: str) -> Parent`
  - `ChildRepository.create(parent_id: uuid.UUID, name: str, profile_image_url: str) -> Child`
  - `UserService.update_me(parent: Parent, data: ParentUpdateRequest, email: str) -> ParentResponse`
  - `UserService.create_child(parent: Parent, data: ChildCreateRequest) -> ChildResponse` (내부 변경)

- [ ] **Step 1: 테스트 파일 업데이트**

`tests/domain/user/test_service.py` 전체를 아래로 교체:

```python
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
```

`tests/domain/user/test_repository.py` 전체를 아래로 교체:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_service.py tests/domain/user/test_repository.py -v
```

Expected: 여러 FAIL (schema/service/repo 미변경 상태이므로)

- [ ] **Step 3: schema.py 전체 교체**

`app/domain/user/schema.py` 전체를 아래로 교체:

```python
import uuid

from pydantic import BaseModel, ConfigDict


class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str


class ParentUpdateRequest(BaseModel):
    name: str


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    profile_image_url: str | None = None


class ChildCreateRequest(BaseModel):
    name: str
    profile_image_url: str


class PresignedUrlRequest(BaseModel):
    content_type: str


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
```

- [ ] **Step 4: repository.py 전체 교체**

`app/domain/user/repository.py` 전체를 아래로 교체:

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child
from app.models.parent import Parent


class ParentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update_parent(self, parent: Parent, name: str) -> Parent:
        parent.name = name
        await self.db.commit()
        await self.db.refresh(parent)
        return parent


class ChildRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_by_parent(self, parent_id: uuid.UUID) -> list[Child]:
        result = await self.db.execute(
            select(Child).where(Child.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def create(
        self, parent_id: uuid.UUID, name: str, profile_image_url: str
    ) -> Child:
        child = Child(
            parent_id=parent_id, name=name, profile_image_url=profile_image_url
        )
        self.db.add(child)
        await self.db.commit()
        await self.db.refresh(child)
        return child
```

- [ ] **Step 5: service.py 전체 교체**

`app/domain/user/service.py` 전체를 아래로 교체:

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.repository import ChildRepository, ParentRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ParentResponse,
    ParentUpdateRequest,
)
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ChildRepository(db)
        self.parent_repo = ParentRepository(db)

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(id=parent.id, name=parent.name, email=email)

    async def update_me(
        self, parent: Parent, data: ParentUpdateRequest, email: str
    ) -> ParentResponse:
        updated = await self.parent_repo.update_parent(parent, data.name)
        return ParentResponse(id=updated.id, name=updated.name, email=email)

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [ChildResponse.model_validate(c) for c in children]

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        child = await self.repo.create(parent.id, data.name, data.profile_image_url)
        return ChildResponse.model_validate(child)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_service.py tests/domain/user/test_repository.py -v
```

Expected: 전체 PASS

- [ ] **Step 7: 전체 테스트 통과 확인**

```bash
uv run pytest -v
```

Expected: 전체 PASS (test_router.py에서 `profile_image_url` 없는 body로 create_child 호출 시 422 가능 — Task 4에서 수정)

- [ ] **Step 8: 커밋**

```bash
git add app/domain/user/schema.py app/domain/user/repository.py app/domain/user/service.py \
    tests/domain/user/test_service.py tests/domain/user/test_repository.py
git commit -m "feat: add ParentUpdateRequest, profile_image_url to child schema/repo/service"
```

---

### Task 4: Router 업데이트

**Files:**
- Modify: `app/domain/user/router.py`
- Modify: `tests/domain/user/test_router.py`

**Interfaces:**
- Consumes:
  - `UserService.update_me(parent, data: ParentUpdateRequest, email: str) -> ParentResponse` (Task 3)
  - `generate_presigned_upload_url(client, key, content_type, expires=300) -> str` (Task 2, `app.core.s3`)
  - `S3ClientDep` (Task 2, `app.core.dependencies`)
  - `PresignedUrlRequest(content_type: str)`, `PresignedUrlResponse(upload_url: str, object_key: str)` (Task 3)
  - `ParentUpdateRequest(name: str)` (Task 3)
  - `CurrentUserWithEmail = Annotated[tuple[Parent, str], Depends(get_current_user_with_email)]`
  - `BadRequestError` (`app.core.exceptions`)
- Produces:
  - `PATCH /users/me` → 200 `ParentResponse`
  - `POST /users/profile-image/presigned-url` → 200 `PresignedUrlResponse`
  - `POST /users/me/children` → 201 `ChildResponse` (`profile_image_url` 필수)
  - `GET /users/me/children` → 200 `list[ChildResponse]` (`profile_image_url` 포함)

- [ ] **Step 1: 테스트 파일 교체**

`tests/domain/user/test_router.py` 전체를 아래로 교체:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_router.py -v
```

Expected: 새 테스트들 FAIL (`update_me`, `profile-image/presigned-url` 엔드포인트 미구현)

- [ ] **Step 3: router.py 전체 교체**

`app/domain/user/router.py` 전체를 아래로 교체:

```python
import uuid as _uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import (
    CurrentUser,
    CurrentUserWithEmail,
    DBSession,
    S3ClientDep,
)
from app.core.exceptions import BadRequestError
from app.core.s3 import generate_presigned_upload_url
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ParentResponse,
    ParentUpdateRequest,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.domain.user.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _get_service(db: DBSession) -> UserService:
    return UserService(db)


@router.get("/me", response_model=ParentResponse)
async def get_me(
    user_with_email: CurrentUserWithEmail,
    service: UserService = Depends(_get_service),
):
    parent, email = user_with_email
    return service.get_me(parent, email)


@router.patch("/me", response_model=ParentResponse)
async def update_me(
    body: ParentUpdateRequest,
    user_with_email: CurrentUserWithEmail,
    service: UserService = Depends(_get_service),
):
    parent, email = user_with_email
    if not body.name or not body.name.strip():
        raise BadRequestError("이름은 비워둘 수 없습니다.")
    return await service.update_me(parent, body, email)


@router.post("/profile-image/presigned-url", response_model=PresignedUrlResponse)
async def get_profile_image_presigned_url(
    body: PresignedUrlRequest,
    user: CurrentUser,
    s3: S3ClientDep,
):
    if not body.content_type.startswith("image/"):
        raise BadRequestError("이미지 파일만 업로드할 수 있습니다.")
    ext = body.content_type.split("/")[-1]
    key = f"profiles/children/{user.id}/{_uuid.uuid4()}.{ext}"
    upload_url = generate_presigned_upload_url(s3, key, body.content_type)
    return PresignedUrlResponse(upload_url=upload_url, object_key=key)


@router.get("/me/children", response_model=list[ChildResponse])
async def get_children(
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    return await service.get_children(user)


@router.post("/me/children", response_model=ChildResponse, status_code=201)
async def create_child(
    body: ChildCreateRequest,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    return await service.create_child(user, body)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_router.py -v
```

Expected: 전체 PASS

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
uv run pytest -v
```

Expected: 전체 PASS

- [ ] **Step 6: 커밋**

```bash
git add app/domain/user/router.py tests/domain/user/test_router.py
git commit -m "feat: add PATCH /users/me and POST /users/profile-image/presigned-url"
```
