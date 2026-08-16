# User Domain (자녀 프로필 + 마이페이지) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `app/domain/user/` 신규 생성 및 학부모 계정 조회·자녀 프로필 CRUD 5개 엔드포인트 구현

**Architecture:** 기존 auth 도메인 패턴(Router → Service → Repository) 동일 적용. 이메일은 Supabase JWT payload의 `email` claim에서 추출하는 `CurrentUserWithEmail` dependency를 신규 추가. 자녀 소유권 확인은 Repository 쿼리에서 `parent_id` 조건으로 한 번에 처리.

**Tech Stack:** FastAPI, SQLAlchemy 2.x (async), python-jose, pytest, pytest-asyncio

## Global Constraints

- Python 3.14, uv 패키지 관리자 (pip/poetry 사용 금지)
- 모든 DB 접근은 `async/await` 유지
- 기존 예외 클래스(`NotFoundError`, `UnauthorizedError`) 재사용, 신규 예외 클래스 추가 없음
- `ChildConsent` 처리는 이번 범위 제외
- `birth_year` 범위 검증 없음 — `int` 타입 체크만
- 브랜치: `feature/user-domain`을 `develop-be`에서 분기 후 `--no-ff` 머지

---

## File Map

| 경로 | 작업 | 역할 |
|------|------|------|
| `app/core/dependencies.py` | 수정 | `CurrentUserWithEmail` dependency 추가 |
| `app/domain/user/__init__.py` | 신규 | 패키지 초기화 |
| `app/domain/user/schema.py` | 신규 | Pydantic 요청/응답 모델 |
| `app/domain/user/repository.py` | 신규 | `children` 테이블 CRUD 쿼리 |
| `app/domain/user/service.py` | 신규 | 비즈니스 로직 |
| `app/domain/user/router.py` | 신규 | 엔드포인트 5개 |
| `main.py` | 수정 | user_router 등록 |
| `pyproject.toml` | 수정 | pytest, pytest-asyncio dev 의존성 추가 |
| `tests/__init__.py` | 신규 | 테스트 패키지 |
| `tests/domain/__init__.py` | 신규 | |
| `tests/domain/user/__init__.py` | 신규 | |
| `tests/test_dependencies.py` | 신규 | CurrentUserWithEmail 단위 테스트 |
| `tests/domain/user/test_schema.py` | 신규 | schema 단위 테스트 |
| `tests/domain/user/test_repository.py` | 신규 | repository 단위 테스트 (AsyncMock) |
| `tests/domain/user/test_service.py` | 신규 | service 단위 테스트 (AsyncMock) |
| `tests/domain/user/test_router.py` | 신규 | 라우터 통합 테스트 (TestClient + 의존성 오버라이드) |

---

## Task 1: 테스트 인프라 설정 + CurrentUserWithEmail dependency

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/domain/__init__.py`
- Create: `tests/domain/user/__init__.py`
- Modify: `app/core/dependencies.py`
- Create: `tests/test_dependencies.py`

**Interfaces:**
- Produces:
  - `get_current_user_with_email(credentials, db) -> tuple[Parent, str]`
  - `CurrentUserWithEmail = Annotated[tuple[Parent, str], Depends(get_current_user_with_email)]`

- [ ] **Step 1: feature 브랜치 생성**

```bash
git checkout develop-be
git checkout -b feature/user-domain
```

- [ ] **Step 2: dev 의존성 추가**

```bash
uv add --dev pytest pytest-asyncio
```

- [ ] **Step 3: pyproject.toml에 pytest 설정 추가**

`pyproject.toml` 파일 끝에 추가:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 4: 테스트 디렉터리 생성**

```bash
mkdir -p tests/domain/user
touch tests/__init__.py tests/domain/__init__.py tests/domain/user/__init__.py
```

- [ ] **Step 5: failing 테스트 작성**

`tests/test_dependencies.py` 신규 생성:

```python
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.exceptions import UnauthorizedError


async def test_get_current_user_with_email_success():
    from app.core.dependencies import get_current_user_with_email
    from app.models.parent import Parent

    parent_id = uuid.uuid4()
    parent = Parent(id=parent_id, name="홍길동")

    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_token"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = parent
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.core.dependencies.verify_supabase_token") as mock_verify:
        mock_verify.return_value = {"sub": str(parent_id), "email": "test@example.com"}
        result_parent, result_email = await get_current_user_with_email(mock_credentials, mock_db)

    assert result_parent == parent
    assert result_email == "test@example.com"


async def test_get_current_user_with_email_no_email_raises_unauthorized():
    from app.core.dependencies import get_current_user_with_email

    mock_credentials = MagicMock()
    mock_credentials.credentials = "token_without_email"
    mock_db = AsyncMock()

    with patch("app.core.dependencies.verify_supabase_token") as mock_verify:
        mock_verify.return_value = {"sub": str(uuid.uuid4())}  # email 없음
        with pytest.raises(UnauthorizedError):
            await get_current_user_with_email(mock_credentials, mock_db)


async def test_get_current_user_with_email_parent_not_found_raises_unauthorized():
    from app.core.dependencies import get_current_user_with_email

    parent_id = uuid.uuid4()
    mock_credentials = MagicMock()
    mock_credentials.credentials = "valid_token"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.core.dependencies.verify_supabase_token") as mock_verify:
        mock_verify.return_value = {"sub": str(parent_id), "email": "test@example.com"}
        with pytest.raises(UnauthorizedError):
            await get_current_user_with_email(mock_credentials, mock_db)
```

- [ ] **Step 6: 테스트 실패 확인**

```bash
uv run pytest tests/test_dependencies.py -v
```

Expected: `ImportError` 또는 `AttributeError` — `get_current_user_with_email` 미존재

- [ ] **Step 7: CurrentUserWithEmail dependency 구현**

`app/core/dependencies.py`에 추가 (기존 import 활용):

```python
async def get_current_user_with_email(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
    db: AsyncSession = Depends(get_db),
) -> tuple[Parent, str]:
    try:
        payload = verify_supabase_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("유효하지 않은 토큰입니다.")
    user_id: str | None = payload.get("sub")
    email: str | None = payload.get("email")
    if not user_id or not email:
        raise UnauthorizedError("유효하지 않은 토큰입니다.")
    result = await db.execute(select(Parent).where(Parent.id == uuid.UUID(user_id)))
    parent = result.scalar_one_or_none()
    if not parent:
        raise UnauthorizedError("프로필이 등록되지 않은 사용자입니다.")
    return parent, email


CurrentUserWithEmail = Annotated[tuple[Parent, str], Depends(get_current_user_with_email)]
```

> 참고: 파일 상단 import에 `from jose import JWTError`가 이미 있는지 확인. 없으면 추가.

- [ ] **Step 8: 테스트 통과 확인**

```bash
uv run pytest tests/test_dependencies.py -v
```

Expected: 3개 PASS

- [ ] **Step 9: 커밋**

```bash
git add app/core/dependencies.py tests/ pyproject.toml uv.lock
git commit -m "feat: add CurrentUserWithEmail dependency and test infrastructure"
```

---

## Task 2: User domain 스키마

**Files:**
- Create: `app/domain/user/__init__.py`
- Create: `app/domain/user/schema.py`
- Create: `tests/domain/user/test_schema.py`

**Interfaces:**
- Consumes: `app/models/child.py::Child` (SQLAlchemy 모델)
- Produces:
  - `ParentResponse(id: UUID, name: str, email: str)`
  - `ChildResponse(id: UUID, name: str, birth_year: int)` — `model_config = ConfigDict(from_attributes=True)`
  - `ChildCreateRequest(name: str, birth_year: int)`
  - `ChildUpdateRequest(name: str | None = None, birth_year: int | None = None)`

- [ ] **Step 1: failing 테스트 작성**

`tests/domain/user/test_schema.py` 신규 생성:

```python
import uuid
import pytest
from app.models.child import Child


def test_child_update_request_all_fields_optional():
    from app.domain.user.schema import ChildUpdateRequest

    req = ChildUpdateRequest()
    assert req.name is None
    assert req.birth_year is None


def test_child_update_request_partial_fields():
    from app.domain.user.schema import ChildUpdateRequest

    req = ChildUpdateRequest(name="지오")
    assert req.name == "지오"
    assert req.birth_year is None


def test_child_response_from_orm_model():
    from app.domain.user.schema import ChildResponse

    child_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child = Child(id=child_id, parent_id=parent_id, name="지오", birth_year=2018)
    resp = ChildResponse.model_validate(child)

    assert resp.id == child_id
    assert resp.name == "지오"
    assert resp.birth_year == 2018


def test_parent_response_fields():
    from app.domain.user.schema import ParentResponse

    parent_id = uuid.uuid4()
    resp = ParentResponse(id=parent_id, name="홍길동", email="test@example.com")

    assert resp.id == parent_id
    assert resp.name == "홍길동"
    assert resp.email == "test@example.com"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_schema.py -v
```

Expected: `ModuleNotFoundError` — `app.domain.user.schema` 미존재

- [ ] **Step 3: 스키마 구현**

`app/domain/user/__init__.py` 신규 생성 (빈 파일):

```python
```

`app/domain/user/schema.py` 신규 생성:

```python
import uuid

from pydantic import BaseModel, ConfigDict


class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    birth_year: int


class ChildCreateRequest(BaseModel):
    name: str
    birth_year: int


class ChildUpdateRequest(BaseModel):
    name: str | None = None
    birth_year: int | None = None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_schema.py -v
```

Expected: 4개 PASS

- [ ] **Step 5: 커밋**

```bash
git add app/domain/user/ tests/domain/user/test_schema.py
git commit -m "feat: add user domain schemas"
```

---

## Task 3: Child Repository

**Files:**
- Create: `app/domain/user/repository.py`
- Create: `tests/domain/user/test_repository.py`

**Interfaces:**
- Consumes: `app/models/child.py::Child`
- Produces:
  - `ChildRepository(db: AsyncSession)`
  - `async get_all_by_parent(parent_id: UUID) -> list[Child]`
  - `async create(parent_id: UUID, name: str, birth_year: int) -> Child`
  - `async get_by_id_and_parent(child_id: UUID, parent_id: UUID) -> Child | None`
  - `async update(child: Child, name: str | None, birth_year: int | None) -> Child`
  - `async delete(child: Child) -> None`

- [ ] **Step 1: failing 테스트 작성**

`tests/domain/user/test_repository.py` 신규 생성:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_repository.py -v
```

Expected: `ModuleNotFoundError` — `app.domain.user.repository` 미존재

- [ ] **Step 3: Repository 구현**

`app/domain/user/repository.py` 신규 생성:

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child


class ChildRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_by_parent(self, parent_id: uuid.UUID) -> list[Child]:
        result = await self.db.execute(
            select(Child).where(Child.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def create(self, parent_id: uuid.UUID, name: str, birth_year: int) -> Child:
        child = Child(parent_id=parent_id, name=name, birth_year=birth_year)
        self.db.add(child)
        await self.db.commit()
        await self.db.refresh(child)
        return child

    async def get_by_id_and_parent(
        self, child_id: uuid.UUID, parent_id: uuid.UUID
    ) -> Child | None:
        result = await self.db.execute(
            select(Child).where(Child.id == child_id, Child.parent_id == parent_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, child: Child, name: str | None, birth_year: int | None
    ) -> Child:
        if name is not None:
            child.name = name
        if birth_year is not None:
            child.birth_year = birth_year
        await self.db.commit()
        await self.db.refresh(child)
        return child

    async def delete(self, child: Child) -> None:
        await self.db.delete(child)
        await self.db.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_repository.py -v
```

Expected: 5개 PASS

- [ ] **Step 5: 커밋**

```bash
git add app/domain/user/repository.py tests/domain/user/test_repository.py
git commit -m "feat: add child repository"
```

---

## Task 4: User Service

**Files:**
- Create: `app/domain/user/service.py`
- Create: `tests/domain/user/test_service.py`

**Interfaces:**
- Consumes:
  - `ChildRepository.get_all_by_parent`, `create`, `get_by_id_and_parent`, `update`, `delete`
  - `ParentResponse`, `ChildResponse`, `ChildCreateRequest`, `ChildUpdateRequest`
  - `NotFoundError`
- Produces:
  - `UserService(db: AsyncSession)`
  - `get_me(parent: Parent, email: str) -> ParentResponse`
  - `async get_children(parent: Parent) -> list[ChildResponse]`
  - `async create_child(parent: Parent, data: ChildCreateRequest) -> ChildResponse`
  - `async update_child(parent: Parent, child_id: UUID, data: ChildUpdateRequest) -> ChildResponse`
  - `async delete_child(parent: Parent, child_id: UUID) -> None`

- [ ] **Step 1: failing 테스트 작성**

`tests/domain/user/test_service.py` 신규 생성:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_service.py -v
```

Expected: `ModuleNotFoundError` — `app.domain.user.service` 미존재

- [ ] **Step 3: Service 구현**

`app/domain/user/service.py` 신규 생성:

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.user.repository import ChildRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    ParentResponse,
)
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ChildRepository(db)

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(id=parent.id, name=parent.name, email=email)

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [ChildResponse.model_validate(c) for c in children]

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        child = await self.repo.create(parent.id, data.name, data.birth_year)
        return ChildResponse.model_validate(child)

    async def update_child(
        self, parent: Parent, child_id: uuid.UUID, data: ChildUpdateRequest
    ) -> ChildResponse:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        child = await self.repo.update(child, data.name, data.birth_year)
        return ChildResponse.model_validate(child)

    async def delete_child(self, parent: Parent, child_id: uuid.UUID) -> None:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        await self.repo.delete(child)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_service.py -v
```

Expected: 7개 PASS

- [ ] **Step 5: 커밋**

```bash
git add app/domain/user/service.py tests/domain/user/test_service.py
git commit -m "feat: add user service"
```

---

## Task 5: User Router + main.py 등록

**Files:**
- Create: `app/domain/user/router.py`
- Modify: `main.py`
- Create: `tests/domain/user/test_router.py`

**Interfaces:**
- Consumes:
  - `CurrentUser`, `CurrentUserWithEmail` (from `app.core.dependencies`)
  - `UserService.get_me`, `get_children`, `create_child`, `update_child`, `delete_child`
  - `MessageResponse` (from `app.domain.auth.schema`)
  - `ParentResponse`, `ChildResponse`, `ChildCreateRequest`, `ChildUpdateRequest`
- Produces: `router` (APIRouter, prefix="/users") — `main.py`에 등록

- [ ] **Step 1: failing 테스트 작성**

`tests/domain/user/test_router.py` 신규 생성:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest tests/domain/user/test_router.py -v
```

Expected: `ImportError` — `app.domain.user.router` 미존재

- [ ] **Step 3: Router 구현**

`app/domain/user/router.py` 신규 생성:

```python
import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, CurrentUserWithEmail, DBSession
from app.domain.auth.schema import MessageResponse
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    ParentResponse,
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
    child_id: uuid.UUID,
    body: ChildUpdateRequest,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    return await service.update_child(user, child_id, body)


@router.delete("/me/children/{child_id}", response_model=MessageResponse)
async def delete_child(
    child_id: uuid.UUID,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    await service.delete_child(user, child_id)
    return MessageResponse(message="자녀 프로필이 삭제되었습니다.")
```

- [ ] **Step 4: main.py에 user_router 등록**

`main.py`에서 기존 `app.include_router(auth_router)` 아래에 추가:

```python
from app.domain.user.router import router as user_router
# ...
app.include_router(user_router)
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
uv run pytest tests/domain/user/test_router.py -v
```

Expected: 7개 PASS

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
uv run pytest tests/ -v
```

Expected: 전체 PASS (22개)

- [ ] **Step 7: 커밋**

```bash
git add app/domain/user/router.py main.py tests/domain/user/test_router.py
git commit -m "feat: add user router and wire up to main"
```

- [ ] **Step 8: feature 브랜치 develop-be로 머지**

```bash
git checkout develop-be
git merge --no-ff feature/user-domain
git branch -d feature/user-domain
```
