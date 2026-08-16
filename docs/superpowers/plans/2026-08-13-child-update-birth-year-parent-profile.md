# 자녀 프로필 수정 API + birth_year + 부모 프로필 이미지 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자녀 프로필 수정 API 추가, birth_year 재추가(나이 계산 포함), 부모 프로필 이미지 지원

**Architecture:** DB 컬럼 추가(Migration 006/007) → Schema/Repository/Service 업데이트(TDD) → Router 업데이트(TDD). ChildResponse에 Pydantic `@computed_field`로 age를 계산. `ParentRepository.update_parent` → `update(parent, data)` 시그니처 변경. Presigned URL 엔드포인트에 `target` 필드 추가로 부모/자녀 경로 구분.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async (AsyncSession), Pydantic v2 (`computed_field`), pytest-asyncio (asyncio_mode=auto), uv

## Global Constraints

- Python 3.14, FastAPI, SQLAlchemy 2.x async — `Mapped` / `mapped_column` 스타일
- uv로 의존성 관리 — pip/poetry 사용 금지
- asyncio_mode = "auto" — `@pytest.mark.asyncio` 데코레이터 불필요
- TDD: 테스트 먼저 작성 → 실패 확인 → 구현 → 통과 확인
- Migration 번호: **006** (birth_year children), **007** (profile_image_url parents)
- `birth_year`: `SmallInteger, nullable=True` — 기존 자녀 행 NULL 허용
- `profile_image_url` (Parent): `String, nullable=True`
- `age` 계산: `datetime.now(timezone.utc).year - birth_year` — birth_year None이면 age None
- Object key 형식: `profiles/parents/{user.id}/{uuid4}.{ext}` (parent) / `profiles/children/{user.id}/{uuid4}.{ext}` (child)
- 소유권 불일치 시 `NotFoundError` (정보 노출 방지)
- 신규 예외 클래스 추가 없음 — `BadRequestError`, `NotFoundError` 재사용
- `ParentRepository.update_parent` → `update(parent, data: ParentUpdateRequest)` 시그니처 변경 (Breaking change — service 동시 수정)

---

### Task 1: DB 모델 + Migration 006/007

**Files:**
- Modify: `app/models/child.py`
- Modify: `app/models/parent.py`
- Create: `alembic/versions/006_add_birth_year_to_children.py`
- Create: `alembic/versions/007_add_profile_image_url_to_parents.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `Child.birth_year: Mapped[int | None]` — Task 2에서 사용
  - `Parent.profile_image_url: Mapped[str | None]` — Task 2에서 사용

- [ ] **Step 1: child.py에 birth_year 추가**

`app/models/child.py`의 imports에 `SmallInteger` 추가:
```python
from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, func
```

`profile_image_url` 필드 다음 줄에 추가:
```python
birth_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
```

최종 Child 필드 순서:
```python
class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # relationships 그대로
```

- [ ] **Step 2: parent.py에 profile_image_url 추가**

`app/models/parent.py`의 `name` 필드 다음 줄에 추가:
```python
profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
```

최종 Parent 클래스:
```python
class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    children: Mapped[list["Child"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
```

- [ ] **Step 3: Migration 006 작성**

`alembic/versions/006_add_birth_year_to_children.py` 신규 생성:

```python
"""add birth_year to children

Revision ID: 006
Revises: 005
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "children",
        sa.Column("birth_year", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("children", "birth_year")
```

- [ ] **Step 4: Migration 007 작성**

`alembic/versions/007_add_profile_image_url_to_parents.py` 신규 생성:

```python
"""add profile_image_url to parents

Revision ID: 007
Revises: 006
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parents",
        sa.Column("profile_image_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parents", "profile_image_url")
```

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
uv run pytest -v
```

Expected: 전체 PASS (nullable 컬럼 추가는 기존 테스트에 영향 없음)

- [ ] **Step 6: 커밋**

```bash
git add app/models/child.py app/models/parent.py \
    alembic/versions/006_add_birth_year_to_children.py \
    alembic/versions/007_add_profile_image_url_to_parents.py
git commit -m "feat: add birth_year to Child and profile_image_url to Parent models"
```

---

### Task 2: Schema + Repository + Service 업데이트

**Files:**
- Modify: `app/domain/user/schema.py`
- Modify: `app/domain/user/repository.py`
- Modify: `app/domain/user/service.py`
- Modify: `tests/domain/user/test_schema.py`
- Modify: `tests/domain/user/test_repository.py`
- Modify: `tests/domain/user/test_service.py`

**Interfaces:**
- Consumes: `Child.birth_year` (Task 1), `Parent.profile_image_url` (Task 1)
- Produces:
  - `ChildResponse(id, name, profile_image_url, birth_year, age)` — `age`는 `@computed_field`
  - `ChildUpdateRequest(name: str | None, profile_image_url: str | None, birth_year: int | None)`
  - `ParentResponse(id, name, email, profile_image_url: str | None = None)`
  - `ParentUpdateRequest(name: str | None, profile_image_url: str | None)`
  - `PresignedUrlRequest(content_type: str, target: Literal["parent", "child"])`
  - `ChildRepository.get_by_id_and_parent(child_id, parent_id) -> Child | None`
  - `ChildRepository.update(child, data: ChildUpdateRequest) -> Child`
  - `ParentRepository.update(parent, data: ParentUpdateRequest) -> Parent` ← `update_parent` 교체
  - `UserService.get_me(parent, email) -> ParentResponse` (profile_image_url 포함)
  - `UserService.update_me(parent, data: ParentUpdateRequest, email) -> ParentResponse`
  - `UserService.update_child(parent, child_id, data: ChildUpdateRequest) -> ChildResponse`

- [ ] **Step 1: 테스트 파일들 업데이트 (먼저 실패 확인)**

`tests/domain/user/test_schema.py` 전체 교체:

```python
import uuid

from app.models.child import Child


def test_child_response_from_orm_model():
    from app.domain.user.schema import ChildResponse

    child_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child = Child(id=child_id, parent_id=parent_id, name="지오")
    resp = ChildResponse.model_validate(child)

    assert resp.id == child_id
    assert resp.name == "지오"
    assert resp.profile_image_url is None
    assert resp.birth_year is None
    assert resp.age is None


def test_child_response_age_computed_from_birth_year():
    from datetime import datetime, timezone

    from app.domain.user.schema import ChildResponse

    child_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    current_year = datetime.now(timezone.utc).year
    child = Child(
        id=child_id, parent_id=parent_id, name="지오", birth_year=current_year - 7
    )
    resp = ChildResponse.model_validate(child)

    assert resp.birth_year == current_year - 7
    assert resp.age == 7


def test_parent_response_fields():
    from app.domain.user.schema import ParentResponse

    parent_id = uuid.uuid4()
    resp = ParentResponse(id=parent_id, name="홍길동", email="test@example.com")

    assert resp.id == parent_id
    assert resp.name == "홍길동"
    assert resp.email == "test@example.com"
    assert resp.profile_image_url is None
```

`tests/domain/user/test_repository.py` 전체 교체:

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
```

`tests/domain/user/test_service.py` 전체 교체:

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
    assert result.profile_image_url is None


def test_get_me_includes_profile_image_url(service, parent):
    parent.profile_image_url = "https://example.com/parent.jpg"

    result = service.get_me(parent, "test@example.com")

    assert result.profile_image_url == "https://example.com/parent.jpg"


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
    service.parent_repo.update = AsyncMock(return_value=updated_parent)

    result = await service.update_me(
        parent, ParentUpdateRequest(name="김철수"), "test@example.com"
    )

    service.parent_repo.update.assert_awaited_once()
    assert result.name == "김철수"
    assert result.email == "test@example.com"


async def test_update_child_returns_updated_response(service, parent):
    from app.domain.user.schema import ChildUpdateRequest

    child_id = uuid.uuid4()
    child = Child(id=child_id, parent_id=parent.id, name="민준", birth_year=2019)
    service.repo.get_by_id_and_parent = AsyncMock(return_value=child)
    service.repo.update = AsyncMock(return_value=child)

    result = await service.update_child(
        parent, child_id, ChildUpdateRequest(name="민준")
    )

    assert result.name == "민준"
    assert result.birth_year == 2019
    assert isinstance(result.age, int)
    assert result.age > 0


async def test_update_child_raises_not_found_when_child_missing(service, parent):
    from app.core.exceptions import NotFoundError
    from app.domain.user.schema import ChildUpdateRequest

    service.repo.get_by_id_and_parent = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.update_child(parent, uuid.uuid4(), ChildUpdateRequest(name="지오"))
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_schema.py tests/domain/user/test_repository.py tests/domain/user/test_service.py -v
```

Expected: 여러 FAIL (구현 미완 상태)

- [ ] **Step 3: schema.py 전체 교체**

`app/domain/user/schema.py` 전체를 아래로 교체:

```python
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field


class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    profile_image_url: str | None = None


class ParentUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    profile_image_url: str | None = None
    birth_year: int | None = None

    @computed_field
    @property
    def age(self) -> int | None:
        if self.birth_year is None:
            return None
        return datetime.now(timezone.utc).year - self.birth_year


class ChildCreateRequest(BaseModel):
    name: str
    profile_image_url: str


class ChildUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None
    birth_year: int | None = None


class PresignedUrlRequest(BaseModel):
    content_type: str
    target: Literal["parent", "child"]


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

from app.domain.user.schema import ChildUpdateRequest, ParentUpdateRequest
from app.models.child import Child
from app.models.parent import Parent


class ParentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update(self, parent: Parent, data: ParentUpdateRequest) -> Parent:
        if data.name is not None:
            parent.name = data.name
        if data.profile_image_url is not None:
            parent.profile_image_url = data.profile_image_url
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

    async def get_by_id_and_parent(
        self, child_id: uuid.UUID, parent_id: uuid.UUID
    ) -> Child | None:
        result = await self.db.execute(
            select(Child).where(Child.id == child_id, Child.parent_id == parent_id)
        )
        return result.scalar_one_or_none()

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

    async def update(self, child: Child, data: ChildUpdateRequest) -> Child:
        if data.name is not None:
            child.name = data.name
        if data.profile_image_url is not None:
            child.profile_image_url = data.profile_image_url
        if data.birth_year is not None:
            child.birth_year = data.birth_year
        await self.db.commit()
        await self.db.refresh(child)
        return child
```

- [ ] **Step 5: service.py 전체 교체**

`app/domain/user/service.py` 전체를 아래로 교체:

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.user.repository import ChildRepository, ParentRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    ParentResponse,
    ParentUpdateRequest,
)
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ChildRepository(db)
        self.parent_repo = ParentRepository(db)

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(
            id=parent.id,
            name=parent.name,
            email=email,
            profile_image_url=parent.profile_image_url,
        )

    async def update_me(
        self, parent: Parent, data: ParentUpdateRequest, email: str
    ) -> ParentResponse:
        updated = await self.parent_repo.update(parent, data)
        return ParentResponse(
            id=updated.id,
            name=updated.name,
            email=email,
            profile_image_url=updated.profile_image_url,
        )

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [ChildResponse.model_validate(c) for c in children]

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        child = await self.repo.create(parent.id, data.name, data.profile_image_url)
        return ChildResponse.model_validate(child)

    async def update_child(
        self, parent: Parent, child_id: uuid.UUID, data: ChildUpdateRequest
    ) -> ChildResponse:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        updated = await self.repo.update(child, data)
        return ChildResponse.model_validate(updated)
```

- [ ] **Step 6: 핵심 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_schema.py tests/domain/user/test_repository.py tests/domain/user/test_service.py -v
```

Expected: 전체 PASS

- [ ] **Step 7: 전체 테스트 실행 (라우터 일부 실패 예상)**

```bash
uv run pytest -v
```

Expected: schema/repo/service 테스트 전체 PASS. `test_get_presigned_url_*` 테스트 2개 FAIL — `PresignedUrlRequest`에 `target` 필드가 추가되어 기존 body로는 422. 이는 Task 3에서 수정.

- [ ] **Step 8: 커밋**

```bash
git add app/domain/user/schema.py app/domain/user/repository.py app/domain/user/service.py \
    tests/domain/user/test_schema.py tests/domain/user/test_repository.py tests/domain/user/test_service.py
git commit -m "feat: add ChildUpdateRequest, birth_year/age to ChildResponse, ParentRepository.update"
```

---

### Task 3: Router 업데이트

**Files:**
- Modify: `app/domain/user/router.py`
- Modify: `tests/domain/user/test_router.py`

**Interfaces:**
- Consumes:
  - `UserService.update_child(parent, child_id: uuid.UUID, data: ChildUpdateRequest) -> ChildResponse` (Task 2)
  - `ChildUpdateRequest(name, profile_image_url, birth_year)` (Task 2)
  - `ParentUpdateRequest(name: str | None, profile_image_url: str | None)` (Task 2 — name이 이제 Optional)
  - `PresignedUrlRequest(content_type, target: Literal["parent","child"])` (Task 2)
  - `ParentResponse(id, name, email, profile_image_url)` (Task 2)
  - `NotFoundError`, `BadRequestError` (`app.core.exceptions`)
- Produces:
  - `PATCH /users/me` — name/profile_image_url optional, 둘 다 None이면 400
  - `PATCH /users/me/children/{child_id}` — 신규, 소유권 확인
  - `POST /users/profile-image/presigned-url` — target에 따라 key 경로 분기

- [ ] **Step 1: test_router.py 전체 교체**

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
    svc.update_child = AsyncMock(
        return_value=ChildResponse(
            id=CHILD_ID,
            name="민준",
            birth_year=2019,
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


def test_update_me_returns_400_when_all_fields_none(client):
    resp = client.patch("/users/me", json={})

    assert resp.status_code == 400


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


def test_update_child_returns_200_with_updated_fields(client):
    resp = client.patch(
        f"/users/me/children/{CHILD_ID}",
        json={"name": "민준", "birth_year": 2019},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "민준"
    assert body["birth_year"] == 2019


def test_update_child_returns_400_when_all_fields_none(client):
    resp = client.patch(f"/users/me/children/{CHILD_ID}", json={})

    assert resp.status_code == 400


def test_update_child_returns_400_for_empty_name(client):
    resp = client.patch(
        f"/users/me/children/{CHILD_ID}",
        json={"name": ""},
    )

    assert resp.status_code == 400


def test_update_child_returns_404_when_not_found(client, mock_svc):
    from app.core.exceptions import NotFoundError

    mock_svc.update_child = AsyncMock(side_effect=NotFoundError())

    resp = client.patch(
        f"/users/me/children/{CHILD_ID}",
        json={"name": "지오"},
    )

    assert resp.status_code == 404


def test_get_presigned_url_returns_200_child_path(client):
    resp = client.post(
        "/users/profile-image/presigned-url",
        json={"content_type": "image/jpeg", "target": "child"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["object_key"].startswith(f"profiles/children/{PARENT_ID}/")
    assert body["object_key"].endswith(".jpeg")


def test_get_presigned_url_returns_200_parent_path(client):
    resp = client.post(
        "/users/profile-image/presigned-url",
        json={"content_type": "image/png", "target": "parent"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["object_key"].startswith(f"profiles/parents/{PARENT_ID}/")
    assert body["object_key"].endswith(".png")


def test_get_presigned_url_returns_400_for_non_image(client):
    resp = client.post(
        "/users/profile-image/presigned-url",
        json={"content_type": "application/pdf", "target": "child"},
    )

    assert resp.status_code == 400
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_router.py -v
```

Expected: 새 테스트들 FAIL (`update_child`, `target` 관련)

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
    ChildUpdateRequest,
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
    if body.name is None and body.profile_image_url is None:
        raise BadRequestError("수정할 항목을 하나 이상 입력해주세요.")
    if body.name is not None and not body.name.strip():
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
    if body.target == "parent":
        key = f"profiles/parents/{user.id}/{_uuid.uuid4()}.{ext}"
    else:
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


@router.patch("/me/children/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: _uuid.UUID,
    body: ChildUpdateRequest,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    if body.name is None and body.profile_image_url is None and body.birth_year is None:
        raise BadRequestError("수정할 항목을 하나 이상 입력해주세요.")
    if body.name is not None and not body.name.strip():
        raise BadRequestError("이름은 비워둘 수 없습니다.")
    return await service.update_child(user, child_id, body)
```

- [ ] **Step 4: 라우터 테스트 통과 확인**

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
git commit -m "feat: add PATCH /users/me/children/{child_id}, target to presigned-url, update PATCH /users/me"
```
