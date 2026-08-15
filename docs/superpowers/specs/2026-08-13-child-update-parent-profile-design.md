# 자녀 프로필 수정 API + birth_year 재추가 + 부모 프로필 이미지 설계

작성일: 2026-08-13

---

## 구현 범위

- Migration 006 — `children.birth_year SMALLINT NULL`
- Migration 007 — `parents.profile_image_url VARCHAR NULL`
- `Child.birth_year: Mapped[int | None]` 추가
- `Parent.profile_image_url: Mapped[str | None]` 추가
- `ChildResponse` — `birth_year`, `age` 추가 (`@computed_field`)
- `ChildUpdateRequest` — name / profile_image_url / birth_year 모두 optional
- `ParentResponse` — `profile_image_url` 추가
- `ParentUpdateRequest` — `profile_image_url` 추가, `name` optional로 변경
- `PresignedUrlRequest` — `target: Literal["parent", "child"]` 추가
- `PATCH /users/me/children/{child_id}` — 신규
- `PATCH /users/me` — profile_image_url 지원 추가
- `POST /users/profile-image/presigned-url` — target 구분자 적용

**범위 외:**
- `POST /users/me/children` 변경 없음 (birth_year 미포함 — 생성 시 선택하지 않음)
- `GET /users/me/children` — ChildResponse 변경으로 자동 반영

---

## DB 변경

### Migration 006
`children` 테이블에 `birth_year SMALLINT NULL` 추가.

```python
revision = "006"
down_revision = "005"

def upgrade():
    op.add_column("children", sa.Column("birth_year", sa.SmallInteger(), nullable=True))

def downgrade():
    op.drop_column("children", "birth_year")
```

### Migration 007
`parents` 테이블에 `profile_image_url VARCHAR NULL` 추가.

```python
revision = "007"
down_revision = "006"

def upgrade():
    op.add_column("parents", sa.Column("profile_image_url", sa.String(), nullable=True))

def downgrade():
    op.drop_column("parents", "profile_image_url")
```

### 모델 변경
```python
# app/models/child.py
birth_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

# app/models/parent.py
profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
```

---

## Schema

```python
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, computed_field

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

class ChildUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None
    birth_year: int | None = None
    # 셋 다 None이면 router에서 400

class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    profile_image_url: str | None = None

class ParentUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None
    # 둘 다 None이면 router에서 400

class PresignedUrlRequest(BaseModel):
    content_type: str
    target: Literal["parent", "child"]

class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
```

---

## API 스펙

### `PATCH /users/me` (변경)
부모 이름 및/또는 프로필 이미지 수정.

```
Request:  { "name": "홍길동", "profile_image_url": "https://..." }
          (두 필드 모두 optional — 최소 1개 필요)
Response: ParentResponse { id, name, email, profile_image_url }
```

검증:
- `name`과 `profile_image_url` 모두 None → `400 BadRequestError`
- `name`이 빈 문자열 또는 공백만 → `400 BadRequestError`

### `PATCH /users/me/children/{child_id}` (신규)
자녀 이름 / 프로필 이미지 / 생년 수정.

```
Request:  { "name": "지오", "birth_year": 2019 }
          (세 필드 모두 optional — 최소 1개 필요)
Response: ChildResponse { id, name, profile_image_url, birth_year, age }
```

검증:
- `child_id`가 현재 부모의 자녀가 아니면 → `404 NotFoundError`
- 세 필드 모두 None → `400 BadRequestError`

### `POST /users/profile-image/presigned-url` (변경)
부모 또는 자녀 프로필 이미지 S3 직접 업로드용 Presigned URL 발급.

```
Request:  { "content_type": "image/jpeg", "target": "parent" | "child" }
Response: { "upload_url": "...", "object_key": "..." }
```

Object key:
- `target="parent"` → `profiles/parents/{user.id}/{uuid4}.{ext}`
- `target="child"` → `profiles/children/{user.id}/{uuid4}.{ext}`

검증:
- `content_type`이 `image/`로 시작하지 않으면 → `400 BadRequestError`

---

## Repository / Service 변경

### ChildRepository 추가
```python
async def get_by_id_and_parent(self, child_id: uuid.UUID, parent_id: uuid.UUID) -> Child | None
async def update(self, child: Child, data: ChildUpdateRequest) -> Child
```

### ParentRepository 추가
```python
async def update(self, parent: Parent, data: ParentUpdateRequest) -> Parent
```
(기존 `update_parent(parent, name)` → `update(parent, data)` 시그니처 변경)

### UserService 변경
```python
async def update_me(self, parent: Parent, data: ParentUpdateRequest, email: str) -> ParentResponse
async def update_child(self, parent: Parent, child_id: uuid.UUID, data: ChildUpdateRequest) -> ChildResponse
```

`get_me`와 `update_me`는 `ParentResponse`를 수동 생성하므로 `profile_image_url=parent.profile_image_url` 명시 필요:
```python
return ParentResponse(
    id=parent.id, name=parent.name, email=email,
    profile_image_url=parent.profile_image_url,
)
```

---

## 비즈니스 로직

### age 계산
`ChildResponse` Pydantic `@computed_field`에서 처리.
```python
age = datetime.now(timezone.utc).year - birth_year  # birth_year가 None이면 None 반환
```

### 자녀 소유권 확인
`get_by_id_and_parent(child_id, parent.id)` 결과 `None` → `NotFoundError` (정보 노출 방지).

### 부분 업데이트 로직
전달된 non-None 필드만 덮어씀. None이 명시적으로 전달된 경우 해당 필드를 NULL로 저장.

---

## 예외 처리

| 상황 | 예외 | HTTP |
|---|---|---|
| child not found / not owned | `NotFoundError` | 404 |
| 수정 필드 전부 None | `BadRequestError` | 400 |
| `content_type` 비이미지 | `BadRequestError` | 400 |
| `name` 빈 문자열/공백 | `BadRequestError` | 400 |
| 토큰 없음 / 미등록 사용자 | `UnauthorizedError` | 401 |

신규 예외 클래스 추가 없음.

---

## 사용자 승인 내용 요약

- 자녀 수정 가능 필드: name, profile_image_url, birth_year (모두 optional)
- birth_year 응답: `birth_year` + 계산된 `age` 함께 반환
- 부모 수정: name + profile_image_url (둘 다 optional, 최소 1개 필요)
- Presigned URL: `target` 필드로 부모/자녀 경로 구분, 단일 엔드포인트 유지
- `POST /users/me/children` 생성 시 birth_year 미포함 (수정으로만 입력)
