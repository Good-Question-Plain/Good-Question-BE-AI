# Vocabulary(학습 리포트) 도메인 설계 — 2026-08-12

## 구현 범위

PRD 3.7 / 4.1 의 학습 리포트와 IMPLEMENTATION_ORDER Phase 6.

| Method | Path | 설명 |
|---|---|---|
| POST | `/reports/{story_id}/generate?child_id=` | 리포트 생성 트리거 (비동기, 202) |
| GET | `/reports/{story_id}?child_id=` | 리포트 조회 (어휘 / 표현 / 논리) |
| GET | `/vocabulary?child_id=&kind=&limit=&offset=` | 아이 어휘 목록 |

## 선행 문제와 결정

### 1. 리포트 저장 테이블 부재

`002_create_new_schema` 에는 어휘·리포트 테이블이 없다. TRD 5장의 `scene_vocabulary` / `child_vocabulary` 는
"사전 정의된 단어를 아이가 저장하는" 모델인데, PRD 3.7 어휘 탭은 "아이 발화에서 LLM이 추출한 어휘"라 성격이 다르다.
→ TRD 안을 버리고 리포트 중심 테이블 2개를 신설한다 (alembic 003).

### 2. 인증 주체 불일치

`CurrentUser` 는 구 모델 `Caregiver` 를 반환하는데 자녀는 `children.parent_id → parents.id` 를 참조한다.
→ **`Caregiver.id` 를 `parents.id` 와 동일한 값으로 취급**하여 `children.parent_id == current_user.id` 로 소유권을 검증한다.
Supabase Auth 전환 시 `Parent.id` 가 `auth.users.id` 와 같아지므로 검증 로직 변경 없이 이어진다.

### 3. 경로 식별자

`story_sessions` 기준이 스키마상 자연스럽지만 문서의 `/reports/{story_id}` 를 유지한다.
자녀가 여러 명이므로 `child_id` 쿼리를 필수로 받고, 서비스가 `(child_id, story_id)` 의 **가장 최근 완료 세션**을 찾아 그 세션의 리포트를 다룬다.

### 4. 라우터 분리

기존 `router.py` 는 `prefix="/reports"` 안에 `@router.get("/vocabulary")` 를 두어 경로가 `/reports/vocabulary` 가 되고
`/reports/{story_id}` 와 충돌했다. → 한 파일에 `reports_router` / `vocabulary_router` 두 개를 두고 `main.py` 에서 각각 등록.

## DB 설계 (alembic 003)

### `learning_reports` — story_session 과 1:1

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| session_id | UUID FK UNIQUE | `story_sessions.id`, CASCADE |
| child_id | UUID FK | `children.id`, CASCADE |
| story_id | UUID FK | `stories.id` |
| status | VARCHAR | `generating` / `completed` / `failed` |
| speech_summary | TEXT NULL | 어휘 탭 상단 말하기 특징 요약 |
| vocabulary_feedback | TEXT NULL | 어휘 피드백 |
| expression_patterns | TEXT[] | 자주 사용한 표현 패턴 |
| expression_items | JSONB | 관점과 공감 / 감정 표현 / 상호작용 |
| logic_items | JSONB | 생각과 이유 / 결과와 해결 |
| analyzer_name | VARCHAR NULL | 분석기 식별자 |
| report_version | VARCHAR | 기본 `stub_v1` |
| failure_reason | TEXT NULL | status=failed 사유 |
| created_at / completed_at | TIMESTAMPTZ | |

`expression_items` / `logic_items` 원소 구조 — PRD 의 "설명 + 발화 인용 + 잘한 점 + 개선 팁" 을 그대로 담는다.

```json
{
  "key": "perspective_empathy",
  "label": "관점과 공감",
  "description": "다른 사람의 감정을 짐작하고 공감하는 표현",
  "quotes": ["아이 발화 인용"],
  "strength": "잘한 점",
  "tip": "개선 팁"
}
```

### `report_vocabularies`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| report_id | UUID FK | `learning_reports.id`, CASCADE |
| child_id | UUID FK | `children.id`, CASCADE — `/vocabulary` 누적 조회용 |
| word | VARCHAR | |
| kind | VARCHAR | `used`(사용한 주요 어휘) / `curious`(궁금해한 어휘) |
| definition | TEXT NULL | |
| example_sentence | TEXT NULL | |
| created_at | TIMESTAMPTZ | |

- `UNIQUE(report_id, word, kind)`
- `INDEX(child_id, kind)`

## 데이터 흐름

### 생성 (POST /reports/{story_id}/generate)

```
소유권 검증 (child.parent_id == current_user.id)
  → (child_id, story_id) 최근 completed 세션 조회, 없으면 404
  → 기존 리포트 확인
      completed  → 그대로 반환 (재생성 안 함)
      generating → 409
      failed/없음 → status=generating 으로 생성 또는 초기화
  → BackgroundTasks 등록 후 202 반환
```

백그라운드 작업은 응답 후 실행되어 요청 스코프 세션(`get_db`)이 이미 닫히므로
`AsyncSessionMaker` 로 **자체 세션을 새로 연다.**

```
백그라운드:
  세션의 child 발화 메시지 + utterance_analyses 로드
  → analyzer.analyze(context) → ReportDraft
  → learning_reports 갱신(status=completed, completed_at)
     + report_vocabularies 일괄 insert
  실패 시 status=failed, failure_reason 기록
```

### 조회 (GET /reports/{story_id})

소유권 검증 → 최근 완료 세션 → 리포트 없으면 404.
`status` 를 응답에 포함하고 본문 필드는 nullable 로 두어, 클라이언트가 `generating` 동안 폴링할 수 있게 한다.

### 어휘 목록 (GET /vocabulary)

소유권 검증 → `report_vocabularies` 를 `child_id` 로 조회, `kind` 필터·페이지네이션 지원. `total` 동봉.

## LLM 연동

이번 범위에서는 **인터페이스만 확정하고 스텁 구현**을 붙인다 (사용자 결정).

`app/domain/vocabulary/analyzer.py`
- `ReportContext` — 스토리 제목, 씬 목표, 아이 발화 목록, 발화 분석 결과
- `ReportDraft` — 리포트 본문 + 어휘 목록
- `ReportAnalyzer` (Protocol) — `async def analyze(ctx) -> ReportDraft`
- `StubReportAnalyzer` — 실제 발화에서 인용문·빈출 어휘를 뽑아 채우고, 피드백 문구는 분석 대기 표시
- `get_report_analyzer()` — 현재 스텁 반환. 실제 Anthropic 구현체로 교체할 지점

스텁 단계라 `ANTHROPIC_API_KEY` 등 신규 환경변수는 추가하지 않는다. 실제 연동 시 함께 도입.

## 변경 파일

```
app/models/report.py              신규 — LearningReport, ReportVocabulary
app/models/__init__.py            신규 모델 등록
app/models/story_session.py       learning_report 관계 추가
alembic/versions/003_...py        신규 — 테이블 2개
app/domain/vocabulary/schema.py   전면 재작성
app/domain/vocabulary/analyzer.py 신규
app/domain/vocabulary/repository.py 신규 작성
app/domain/vocabulary/service.py  신규 작성
app/domain/vocabulary/router.py   전면 재작성 (라우터 2개)
main.py                           라우터 등록
docs/IMPLEMENTATION_ORDER.md      Phase 6 갱신
```

## 사용자 승인 내용

- 엔드포인트는 기존 `story_id` 경로 유지, `child_id` 등 쿼리 파라미터 추가
- 소유권 검증은 `Caregiver.id` 를 `parents.id` 로 간주
- 리포트 생성은 BackgroundTasks 비동기, 202 반환
- LLM 은 인터페이스 + 스텁까지만
- `IMPLEMENTATION_ORDER.md` 를 확정된 시그니처로 수정
