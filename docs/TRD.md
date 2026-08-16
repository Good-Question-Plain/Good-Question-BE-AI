# TRD (Technical Requirements Document)

> AI 기능(STT, TTS, LLM 분석) 관련 설계는 별도 문서로 분리 예정. 본 문서는 인프라·DB·인증·캐싱 설계를 다룬다.

---

## 1. 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| Framework | FastAPI | |
| ORM | SQLAlchemy 2.x (async) | `AsyncSession` 기반 |
| DB | PostgreSQL 16 | |
| Cache / Session Store | Redis 7 | |
| Migration | Alembic | docker compose exec로 관리 |
| Auth | JWT + SMTP 2차 인증 | Access / Refresh Token 분리 |
| 이메일 | aiosmtplib | 비동기 SMTP |
| 파일 스토리지 | AWS S3 | IAM 최소 권한, Presigned URL 방식 |
| AWS SDK | boto3 | |
| 패키지 관리 | uv | pip / poetry 사용 금지 |
| 컨테이너 | Docker + Docker Compose | api / db / redis / cloudflared |
| 배포 | Cloudflare Tunnel | 서버 포트 직접 오픈 없이 터널로만 노출 |
| CI/CD | GitHub Actions | |

> **파일 스토리지 전환 기준**: 월 오디오 이그레스가 100GB를 초과하는 시점에 Cloudflare R2 전환 검토 (S3 호환 API라 boto3 코드 변경 최소화)

---

## 2. 프로젝트 구조

```
app/
├── core/                   # 전역 인프라 — Spring @Bean 영역
│   ├── config.py           # 환경변수 (pydantic-settings)
│   ├── logging.py          # 구조화 로깅 설정
│   ├── security.py         # JWT 발급·검증
│   ├── smtp.py             # 이메일 클라이언트
│   ├── redis.py            # Redis 클라이언트 싱글턴
│   ├── s3.py               # S3 클라이언트 및 Presigned URL 생성
│   ├── exceptions.py       # 전역 예외 핸들러
│   └── dependencies.py     # DI 등록소 (Annotated + Depends)
│
├── db/
│   ├── base.py             # DeclarativeBase
│   └── session.py          # AsyncSessionMaker, get_db
│
├── domain/                 # 기능 단위 모듈
│   ├── auth/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── schema.py
│   ├── user/
│   ├── story/
│   ├── progress/
│   └── vocabulary/
│
├── models/                 # SQLAlchemy 모델 (전 도메인 공유)
│   ├── caregiver.py
│   ├── child_profile.py
│   ├── story.py
│   ├── scene.py
│   ├── progress.py
│   ├── conversation.py
│   └── vocabulary.py
│
└── main.py                 # FastAPI 앱 진입점, 라우터 등록
```

---

## 3. 레이어드 아키텍처

```
Router      → 요청 수신, 입력 검증 (Pydantic schema), 응답 직렬화
Service     → 비즈니스 로직, 트랜잭션 경계
Repository  → DB 접근 전담 (SQLAlchemy AsyncSession)
core/       → 전역 인프라 (JWT, Redis, SMTP, S3, 로깅)
```

- 도메인 간 직접 참조 금지. 필요한 경우 Service → Repository를 통해서만 접근
- 모든 레이어 비동기(`async/await`) 유지

---

## 4. 의존성 주입 (Spring Bean 방식)

`core/dependencies.py`를 Bean 등록소로 사용한다. `@lru_cache`로 싱글턴을 보장하고, `Annotated` 타입으로 주입부를 선언해 Router에서 간결하게 사용한다.

```python
# core/dependencies.py

# 싱글턴 (앱 생애주기 동안 1회 생성)
@lru_cache
def get_settings() -> Settings: ...

@lru_cache
def get_redis() -> Redis: ...

@lru_cache
def get_s3_client() -> S3Client: ...

# 요청 단위 (매 요청마다 생성 → 자동 close)
async def get_db() -> AsyncGenerator[AsyncSession, None]: ...

# 인증 게이트 (JWT 검증 → User 객체 반환)
async def get_current_user(token: str, db: DBSession) -> Caregiver: ...

# Annotated 타입 별칭 (Router에서 사용)
SettingsDep  = Annotated[Settings,      Depends(get_settings)]
DBSession    = Annotated[AsyncSession,  Depends(get_db)]
RedisDep     = Annotated[Redis,         Depends(get_redis)]
CurrentUser  = Annotated[Caregiver,     Depends(get_current_user)]
```

```python
# 사용 예시 (Router)
@router.get("/me")
async def get_me(user: CurrentUser, db: DBSession):
    return await user_service.get_profile(db, user.id)
```

---

## 5. DB 설계

### ERD 개요

```
caregiver ──< child_profile
story     ──< scene ──< scene_vocabulary
child_profile ──< story_progress >── story
child_profile ──< conversation_turn >── scene
child_profile ──< child_vocabulary >── scene_vocabulary
```

### 테이블 상세

#### `caregiver`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| hashed_password | VARCHAR | 소셜 로그인 시 NULL |
| social_provider | ENUM | `email / kakao / google / naver` |
| social_id | VARCHAR | 소셜 고유 ID |
| is_verified | BOOLEAN | 이메일 인증 완료 여부 |
| created_at | TIMESTAMP | |

#### `child_profile`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| caregiver_id | UUID FK | |
| name | VARCHAR | |
| age | INTEGER | |
| created_at | TIMESTAMP | |

#### `story`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| title | VARCHAR | |
| thumbnail_url | VARCHAR | S3 URL |
| category | VARCHAR | |
| estimated_minutes | INTEGER | 예상 소요 시간 |
| description | TEXT | 소개·배경·아이 역할 |
| is_published | BOOLEAN | |
| created_at | TIMESTAMP | |

#### `scene`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| story_id | UUID FK | |
| order | INTEGER | 씬 순서 |
| image_url | VARCHAR | S3 URL |
| character_name | VARCHAR | |
| character_dialogue | TEXT | 캐릭터 대사 |
| audio_url | VARCHAR | S3 URL (캐릭터 대사 오디오) |
| max_turns | INTEGER | 최대 대화 턴 수 |

#### `scene_vocabulary`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| scene_id | UUID FK | |
| word | VARCHAR | |
| definition | TEXT | |
| example_sentence | TEXT | |

#### `story_progress`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| story_id | UUID FK | |
| current_scene_id | UUID FK | |
| is_completed | BOOLEAN | |
| updated_at | TIMESTAMP | |

#### `conversation_turn`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| scene_id | UUID FK | |
| speaker | ENUM | `character / child` |
| content | TEXT | 발화 내용 (STT 결과 또는 캐릭터 대사) |
| turn_order | INTEGER | |
| created_at | TIMESTAMP | |

#### `child_vocabulary`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| child_profile_id | UUID FK | |
| scene_vocabulary_id | UUID FK | |
| saved_at | TIMESTAMP | |

---

## 6. 인증 설계

### 이메일 회원가입 (SMTP 2차 인증)

```
1. POST /auth/register
   → 이메일·비밀번호 수신, OTP 생성
   → Redis: SET otp:{email} = OTP (TTL 5분)
   → aiosmtplib으로 인증 메일 발송

2. POST /auth/verify-email
   → OTP 검증 → caregiver.is_verified = True
   → Redis: OTP 키 삭제

3. POST /auth/login
   → Access Token (15분) + Refresh Token (7일) 발급
   → Redis: SET refresh:{user_id} = Refresh Token (TTL 7일)

4. POST /auth/refresh
   → Redis에서 Refresh Token 검증 → 새 Access Token 발급

5. POST /auth/logout
   → Redis: refresh:{user_id} 즉시 삭제
```

### 소셜 로그인 (카카오·구글·네이버)

OAuth 2.0 Authorization Code Flow 사용. 라이브러리는 `httpx`로 직접 구현 (fastapi[standard]에 포함).

#### 플로우

```
1. GET /auth/{provider}/login
   → 각 provider의 OAuth 인증 URL로 리다이렉트
      (client_id, redirect_uri, scope, state 포함)

2. GET /auth/{provider}/callback   ← provider가 리다이렉트하는 엔드포인트
   → Authorization Code 수신
   → httpx로 provider Token URL에 code 교환 요청
   → 받은 access_token으로 provider Userinfo URL 호출
   → 이메일·소셜 ID 추출
   → caregiver upsert (social_provider + social_id 기준)
   → 자체 Access Token + Refresh Token 발급 (이하 이메일 로그인과 동일)
```

#### Provider별 엔드포인트

| Provider | Auth URL | Token URL | Userinfo URL | Scope |
|----------|----------|-----------|--------------|-------|
| Google | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` | `https://www.googleapis.com/oauth2/v2/userinfo` | `openid email profile` |
| Kakao | `https://kauth.kakao.com/oauth/authorize` | `https://kauth.kakao.com/oauth/token` | `https://kapi.kakao.com/v2/user/me` | `profile_nickname account_email` |
| Naver | `https://nid.naver.com/oauth2.0/authorize` | `https://nid.naver.com/oauth2.0/token` | `https://openapi.naver.com/v1/nid/me` | `name email` |

#### CSRF 방지 (state 파라미터)

```
1. /auth/{provider}/login 요청 시 서버에서 랜덤 state 값 생성
2. Redis: SET oauth_state:{state} = "1" (TTL 10분)
3. callback 수신 시 state 값을 Redis에서 검증 후 삭제
```

#### 환경변수

```
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
KAKAO_CLIENT_ID, KAKAO_CLIENT_SECRET
NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
OAUTH_REDIRECT_BASE_URL    # 예: https://yourdomain.com
```

### IAM 권한 (S3)

- IAM 계정에 부여할 최소 권한: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`
- Access Key / Secret Key → 환경변수로 관리 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- 버킷 퍼블릭 접근 차단, 모든 접근은 Presigned URL 경유

---

## 7. 캐싱 전략 (Redis)

| 키 패턴 | 용도 | TTL |
|---------|------|-----|
| `otp:{email}` | 이메일 인증 OTP | 5분 |
| `oauth_state:{state}` | 소셜 로그인 CSRF 방지 state | 10분 |
| `refresh:{user_id}` | Refresh Token | 7일 |
| `story:{story_id}` | 스토리 콘텐츠 | 1시간 |
| `scene:{scene_id}` | 씬 콘텐츠 | 1시간 |
| `recommended:{child_age}` | 추천 스토리 목록 | 10분 |
| `conv:{child_id}:{scene_id}` | 진행 중 대화 컨텍스트 | 세션 단위 |

**대화 컨텍스트 처리 흐름:**
- 씬 진행 중: 대화 턴을 Redis에 append
- 씬 완료 또는 최대 턴 도달 시: Redis 데이터를 `conversation_turn` 테이블에 일괄 저장 후 키 삭제

---

## 8. Docker Compose 구성

### 서비스 구성

```yaml
# docker-compose.yml

services:
  api:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./app:/app/app        # 개발 환경 핫리로드용

  db:
    image: postgres:16-alpine
    env_file: .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token $$CLOUDFLARE_TUNNEL_TOKEN
    env_file: .env
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

### Alembic 마이그레이션 명령어

```bash
# 마이그레이션 적용
docker compose exec api alembic upgrade head

# 새 마이그레이션 파일 자동 생성
docker compose exec api alembic revision --autogenerate -m "설명"

# 한 단계 롤백
docker compose exec api alembic downgrade -1

# 현재 버전 확인
docker compose exec api alembic current
```

---

## 9. CI/CD (GitHub Actions)

### 파이프라인 흐름

```
Push to main
  ├── 1. Lint / Type Check
  │       ruff check .
  │       mypy app/
  │
  ├── 2. Docker 이미지 빌드 및 Push
  │       docker build → GHCR (ghcr.io/{repo})
  │
  ├── 3. 서버 배포
  │       SSH → docker compose pull
  │              docker compose up -d
  │
  └── 4. 마이그레이션 자동 실행
          docker compose exec api alembic upgrade head
```

### 환경변수 관리

- 민감 정보(DB 비밀번호, JWT Secret, AWS Key, Cloudflare Token 등)는 GitHub Secrets에 등록
- 배포 시 서버의 `.env` 파일로 주입

---

## 10. 배포 구성 (Cloudflare Tunnel)

```
외부 HTTPS 요청
  └── Cloudflare (TLS 종료, DDoS 방어)
        └── cloudflared (Docker 서비스)
              └── api:8000 (Docker 내부 HTTP)
```

- 서버 방화벽에서 8000 포트 외부 오픈 불필요
- SSL 인증서 관리 불필요 (Cloudflare가 처리)
- `CLOUDFLARE_TUNNEL_TOKEN`은 Cloudflare Zero Trust 대시보드에서 발급
