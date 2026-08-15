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
> ⚠️ 아래 표는 TRD 5장 기준의 초기 계획이다. 실제로는 `alembic/002` 에서 다른 이름·구조로 반영되었다
> (`parents`, `children`, `child_consents`, `stories`, `story_scenes`, `story_sessions`, `messages`,
> `utterance_analyses`, `post_activity_results`). 어휘 테이블은 Phase 6 의 리포트 테이블로 대체됨.

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
| `GET /users/me` — 학부모 계정 정보 조회 | ⬜ |
| `GET /users/me/children` — 자녀 프로필 목록 | ⬜ |
| `POST /users/me/children` — 자녀 프로필 추가 | ⬜ |
| `PATCH /users/me/children/{child_id}` — 자녀 프로필 수정 | ⬜ |
| `DELETE /users/me/children/{child_id}` — 자녀 프로필 삭제 | ⬜ |

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
| ↳ `utterance_analyses.detected_elements` 는 `[{"element":"EMOTION","evidence":"..."}]` 객체 배열로 저장 (Phase 6 대표 발화 선정의 입력) | ⬜ |
| `PATCH /progress/{story_id}/scenes/{scene_id}/complete` — 씬 완료 처리 (conversation_turn DB 저장) | ⬜ |
| Redis 대화 컨텍스트 관리 (`conv:{child_id}:{scene_id}`) | ⬜ |

---

## Phase 6 — Vocabulary 도메인 (학습 리포트)

> `app/domain/vocabulary/`. 설계 문서: `docs/designs/vocabulary-report 2026-08-12 23:05.md`
> 리포트는 `story_sessions` 단위로 생성되므로 `child_id` 쿼리로 아이를 특정하고, 서비스가 최근 완료 세션을 찾는다.

| 작업 | 상태 |
|------|------|
| `app/models/report.py` (learning_report + report_vocabulary) | ✅ |
| `alembic/003` — learning_reports, report_vocabularies 마이그레이션 | ✅ |
| `POST /reports/{story_id}/generate?child_id=` — 리포트 생성 트리거 (BackgroundTasks, 202) | ✅ |
| `GET /reports/{story_id}?child_id=` — 학습 리포트 조회 (어휘/표현/논리 전체) | ✅ |
| `GET /vocabulary?child_id=&kind=&limit=&offset=` — 아이가 사용·궁금해한 어휘 목록 조회 | ✅ |
| `analyzer.py` — 리포트 분석기 인터페이스 + 스텁 구현 | ✅ |
| 대표 발화 선정 (규칙 점수 + 동점 처리) — `docs/designs/representative-utterance 2026-08-12 23:25.md` | ✅ |
| `alembic/004` — learning_reports 대표 발화 컬럼 추가 | ✅ |
| 실제 LLM(Anthropic) 분석기 — `docs/designs/llm-report-analyzer 2026-08-13 00:30.md` | ✅ |
| OpenAI `make_report` 분석기 — `docs/designs/story-ai 2026-08-15 13:20.md` | ✅ |
| 리포트 화면 대응 (집에서 이어가볼까요 / 이전·다음 리포트 / 헤더 정보) — `docs/designs/report-screen-coverage 2026-08-13 12:50.md` | ✅ |
| `alembic/005` — story_topic_questions, daily_life_questions 컬럼 추가 | ✅ |
| `alembic/006` — scene_vocabularies, child_vocabularies (궁금한 단어) | ✅ |
| 완료된 리포트 재생성 + `enqueue_for_completed_session` (이야기 완료 훅) | ✅ |
| 궁금한 단어(`kind=curious`)를 세션 선택 결과와 병합 | ✅ |

> 남은 의존성
> - 소유권 검증은 `Caregiver.id == parents.id` 가정에 의존한다.
>   Phase 3(User 도메인)에서 `parents` 레코드 생성이 붙어야 실제로 동작한다.
> - `OPENAI_API_KEY` 가 있으면 `make_report` 분석기를 쓴다. 없고 `ANTHROPIC_API_KEY` 만 있으면 기존 Anthropic 분석기, 둘 다 없으면 스텁.
> - `POST /reports/{story_id}/generate` 는 같은 세션의 완료 리포트가 있어도 이번 회차로 다시 만든다.
>   이야기 완료 시 자동 생성은 `ReportService.enqueue_for_completed_session` 을 Phase 5 완료 처리에서 호출하면 붙는다.
