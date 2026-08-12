# 구현 순서 및 진행 상황

> 이 문서는 작업이 진행될 때마다 상태를 갱신한다.  
> 상태 표기: ✅ 완료 | 🔄 진행 중 | ⬜ 미시작

---

## 현재 완료된 기반 작업

| 항목 | 상태 |
|------|------|
| `app/core/` (config, security, smtp, redis, exceptions, dependencies) | ✅ |
| `app/db/` (base, session) | ✅ |
| `app/models/caregiver.py` | ✅ |
| `app/domain/auth/` (register, verify-email, login, refresh, logout, social) | ✅ |
| `alembic/001` — caregiver 테이블 마이그레이션 | ✅ |

---

## Phase 1 — Auth 보완

> 기존 auth 도메인 확장. AI 연동 없음.

| 작업 | 상태 |
|------|------|
| `POST /auth/forgot-password` — 비밀번호 재설정 메일 발송 (OTP 재활용) | ✅ |
| `POST /auth/reset-password` — 새 비밀번호 설정 | ✅ |
| `DELETE /auth/me` — 회원탈퇴 | ✅ |

---

## Phase 2 — DB 스키마 전체 확정

> Phase 3~6 모두의 선행 조건. 반드시 먼저 완료.

| 작업 | 상태 |
|------|------|
| `app/models/child_profile.py` | ⬜ |
| `app/models/story.py` (story + scene + scene_vocabulary) | ⬜ |
| `app/models/progress.py` (story_progress + conversation_turn) | ⬜ |
| `app/models/vocabulary.py` (child_vocabulary) | ⬜ |
| `alembic/002` — child_profile 마이그레이션 | ⬜ |
| `alembic/003` — story, scene, scene_vocabulary 마이그레이션 | ⬜ |
| `alembic/004` — story_progress, conversation_turn, child_vocabulary 마이그레이션 | ⬜ |

---

## Phase 3 — User 도메인 (자녀 프로필 + 마이페이지)

> `app/domain/user/` 신규 생성. AI 연동 없음.

| 작업 | 상태 |
|------|------|
| `GET /users/me` — 학부모 계정 정보 조회 | ✅ |
| `GET /users/me/children` — 자녀 프로필 목록 | ✅ |
| `POST /users/me/children` — 자녀 프로필 추가 | ✅ |
| `PATCH /users/me/children/{child_id}` — 자녀 프로필 수정 | ✅ |
| `DELETE /users/me/children/{child_id}` — 자녀 프로필 삭제 | ✅ |

---

## Phase 4 — Story 도메인 (스토리 탐색)

> `app/domain/story/` 신규 생성. Redis 캐시 활용. AI 연동 없음.

| 작업 | 상태 |
|------|------|
| `GET /stories` — 스토리 목록 (카테고리 필터, 페이지네이션) | ⬜ |
| `GET /stories/recommended` — 추천 스토리 3개 (Redis 10분 캐시) | ⬜ |
| `GET /stories/{story_id}` — 스토리 상세 (Redis 1시간 캐시) | ⬜ |
| `GET /stories/{story_id}/scenes` — 씬 목록 조회 | ⬜ |

---

## Phase 5 — Progress 도메인 (스토리 진행 + 음성 인터랙션)

> `app/domain/progress/` 신규 생성. STT 및 LLM 연동 포함.

| 작업 | 상태 |
|------|------|
| `POST /progress/{story_id}/start` — 스토리 시작 (story_progress 생성) | ⬜ |
| `GET /progress/active` — 진행 중인 스토리 1개 조회 (메인 화면) | ⬜ |
| `GET /progress/{story_id}` — 현재 진행 상태 조회 | ⬜ |
| `POST /progress/{story_id}/scenes/{scene_id}/speak` — 아이 발화 제출 (STT → AI 분석 → 후속질문 or 다음 씬) | ⬜ |
| `PATCH /progress/{story_id}/scenes/{scene_id}/complete` — 씬 완료 처리 (conversation_turn DB 저장) | ⬜ |
| Redis 대화 컨텍스트 관리 (`conv:{child_id}:{scene_id}`) | ⬜ |

---

## Phase 6 — Vocabulary 도메인 (학습 리포트)

> `app/domain/vocabulary/` 신규 생성. LLM 기반 리포트 생성 포함.

| 작업 | 상태 |
|------|------|
| `POST /reports/{story_id}/generate` — 스토리 완료 후 LLM 리포트 생성 트리거 | ⬜ |
| `GET /reports/{story_id}` — 학습 리포트 조회 (어휘/표현/논리 전체) | ⬜ |
| `GET /vocabulary` — 아이가 사용·궁금해한 어휘 목록 조회 | ⬜ |
