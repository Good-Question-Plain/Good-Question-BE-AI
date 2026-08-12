# 프로필 이미지 + 부모 정보 수정 설계

작성일: 2026-08-13

---

## 구현 범위

- `app/core/s3.py` 신규 — S3 클라이언트 + Presigned URL 생성
- `POST /users/profile-image/presigned-url` — 자녀 프로필 이미지 업로드용 Presigned URL 발급
- `PATCH /users/me` — 부모 이름 수정
- `POST /users/me/children` — `profile_image_url` 필수 필드 추가
- `GET /users/me/children` — 응답에 `profile_image_url` 추가
- `Child` 모델 + Migration 004 — `profile_image_url` 컬럼 추가

**범위 외:**
- 부모 프로필 이미지 (`Parent` 모델 변경 없음)
- `POST /auth/sync-profile` 변경 없음

---

## 파일 구조

### 신규 생성
- `app/core/s3.py`
- `alembic/versions/004_add_profile_image_url_to_children.py`

### 수정
- `app/core/dependencies.py` — `S3ClientDep` 추가
- `app/models/child.py` — `profile_image_url: Mapped[str | None]` 추가
- `app/domain/user/schema.py` — `ChildCreateRequest`, `ChildResponse`, `ParentUpdateRequest` 추가
- `app/domain/user/repository.py` — `update_parent`, `create` 시그니처에 `profile_image_url` 추가
- `app/domain/user/service.py` — `update_me`, `create_child` 수정
- `app/domain/user/router.py` — `PATCH /users/me`, `POST /users/profile-image/presigned-url` 추가

---

## API 스펙

### `POST /users/profile-image/presigned-url`
자녀 프로필 이미지 S3 직접 업로드용 Presigned URL 발급.

```
Request:  { "content_type": "image/jpeg" }
Response: { "upload_url": "https://...", "object_key": "profiles/children/{parent_id}/{uuid}.jpg" }
```

- `content_type`이 `image/`로 시작하지 않으면 → `400 BadRequestError`
- Presigned URL 유효시간: 300초 (5분)
- Object key: `profiles/children/{parent_id}/{uuid4}.{ext}` — parent_id로 경로 격리

### `PATCH /users/me`
부모 이름 수정.

```
Request:  { "name": "홍길동" }
Response: { "id": "uuid", "name": "홍길동", "email": "..." }
```

- `name`이 없거나 빈 문자열이면 → `400 BadRequestError`

### `POST /users/me/children` (변경)
자녀 프로필 생성. `profile_image_url` 필수 추가.

```
Request:  { "name": "지오", "profile_image_url": "https://s3.amazonaws.com/..." }
Response: { "id": "uuid", "name": "지오", "profile_image_url": "https://..." }
```

### `GET /users/me/children` (변경)
응답에 `profile_image_url` 추가.

```
Response: [{ "id": "uuid", "name": "지오", "profile_image_url": "https://..." }]
```

---

## S3 설계

### `app/core/s3.py`

```python
@lru_cache
def get_s3_client() -> S3Client:
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def generate_presigned_upload_url(
    client: S3Client,
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

### `app/core/dependencies.py` 추가

```python
S3ClientDep = Annotated[S3Client, Depends(get_s3_client)]
```

---

## DB 변경

### `Child` 모델
```python
profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
```

### Migration 004
`children` 테이블에 `profile_image_url VARCHAR NULL` 컬럼 추가.

---

## 데이터 흐름

```
클라이언트
  │
  ├─① POST /users/profile-image/presigned-url { content_type }
  │       └─ 서버: S3 Presigned PUT URL + object_key 반환
  │
  ├─② PUT {upload_url}  (클라이언트 → S3 직접)
  │
  └─③ POST /users/me/children { name, profile_image_url }
          └─ 서버: children 테이블 저장
```

---

## 예외 처리

| 상황 | 예외 | HTTP |
|------|------|------|
| `content_type`이 `image/`로 시작하지 않음 | `BadRequestError` | 400 |
| `PATCH /users/me` name 없거나 빈 문자열 | `BadRequestError` | 400 |
| 토큰 없음 / 미등록 사용자 | `UnauthorizedError` | 401 |

신규 예외 클래스 추가 없음, 기존 `BadRequestError` 재사용.

---

## 사용자 승인 내용 요약

- S3 업로드: Presigned PUT URL 방식 (클라이언트 직접 업로드)
- 프로필 이미지: 자녀 전용 (부모 이미지 없음)
- `POST /auth/sync-profile` 변경 없음
- `PATCH /users/me`: name만 수정 가능
- Presigned URL 엔드포인트: 단일 공용 (자녀 전용)
