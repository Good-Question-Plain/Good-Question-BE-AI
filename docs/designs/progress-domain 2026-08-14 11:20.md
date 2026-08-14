# Progress 도메인 설계 (스토리 진행 + 음성 인터랙션)

작성일: 2026-08-14  
Phase: 5

---

## 구현 범위

- `POST /progress/{story_id}/start` — 세션 시작 또는 이어하기
- `GET /progress/active` — 진행 중인 스토리 1개 (메인 화면)
- `GET /progress/{story_id}` — 현재 세션 상태
- `POST /progress/{story_id}/steps/{step_index}` — 해당 단계 진입 + 콘텐츠 반환
- `POST /progress/{story_id}/steps/{step_index}/speak` — 아이 발화 (STT → 검증 → 대사)
- `POST /progress/{story_id}/steps/{step_index}/complete` — 내레이션 단계 완료
- Redis 대화 컨텍스트 `conv:{session_id}:{scene_id}`

이번 범위 제외:

- `make_report` — Phase 6
- 사후활동 (`post_activity_results`)
- TTS / 캐릭터 음성 재생
- 콘텐츠 시딩 자체 (스키마만 콘텐츠가 들어갈 수 있게 맞춤)
- 캐릭터 테이블, 캐릭터 초상 이미지

---

## 콘텐츠 모델 (노션 MVP 기준)

한 이야기는 씬이 두 종류로 번갈아 구성된다. `step_index` = `scene_order` (1부터).

| scene_type | 예 | 아이 발화 | 채워지는 필드 |
|------------|----|-----------|----------------|
| `narration` | 도입, 전개1~4 | 없음 | `scene_description`, `image_url` |
| `dialogue` | 대화1~4 | 있음 | `character_*`, `scene_goal`, `required_elements`, `max_turns` |

미션은 별도 타입이 아니다. 대화 씬에 `mission_condition`이 있으면 그 씬이 미션 씬이다. 프론트 `kind`는 서버가 계산한다.

- `narration`
- `dialogue` — 미션 없음
- `mission` — `dialogue` + `mission_condition` 존재

프론트가 말한 `GET /stories/{storyId}/steps/{stepIndex}`의 역할(타입, 줄거리, 배경, 캐릭터 대사, 현재 단계 3/8)은 **진행 중인 세션 위에서** 의미가 있으므로 progress 경로로 둔다. GET이면 `current_scene_id`를 갱신할 수 없어 이어하기가 깨진다.

---

## 기본안 (미응답 항목)

| 항목 | 기본안 | 이유 |
|------|--------|------|
| 콘텐츠 slug (`s_banggui_…`, `sc_banggui_03`) | PK는 UUID 유지. `stories.content_key`, `story_scenes.content_key` 추가. API 경로는 UUID | 기존 모델·프론트 관례와 맞음. 시딩·콘텐츠팀 식별은 slug |
| 캐릭터 표시 이름 | 캐릭터 테이블은 만들지 않음. `character_key`(slug) + `character_name`(표시명, "며느리") | 씬마다 화자가 다르고, 초상 이미지는 스펙에 없음 |
| `ㅇㅇ아` 치환 | 응답 시 `{child_name}`과 `ㅇㅇ`을 아이 이름으로 치환. DB에는 원문 저장 | 기존 원고(`ㅇㅇ`)와 이후 원고(`{child_name}`) 둘 다 수용 |
| `utterance_analyses` | 행은 만든다. `utterance_validity`만 채움. `child_intent`·`detected_elements`는 nullable | 나중에 요소 추출이 붙어도 테이블을 다시 안 만듦 |
| 잘못된 발화 반복 | 저장하지 않고 되묻기. 연속 3회 실패 시 저장하고 턴 진행 | 무한 루프 방지. 상한은 상수 `MAX_INVALID_RETRIES = 3` |

아니라고 하시면 구현 전에 고친다.

---

## 파일 구조

### 신규
```
app/domain/progress/
├── __init__.py
├── router.py
├── service.py
├── repository.py
├── schema.py
└── ai.py          # StoryAI Protocol + StubStoryAI + get_story_ai()
```

### 수정
- `app/models/story.py` — 씬 컬럼 재구성
- `app/models/message.py` — `UtteranceAnalysis.child_intent` nullable
- `app/domain/story/schema.py` — difficulty 한국어, 씬 응답에 `scene_type`·nullable
- `main.py` — progress_router 등록 (`/progress/active`를 `/{story_id}`보다 먼저)

### 마이그레이션
`alembic/008_progress_scene_schema.py`

---

## 스키마 변경

### stories
| 변경 | 내용 |
|------|------|
| + `content_key` | `String`, unique, nullable — 시딩 시 채움 |

`difficulty` 컬럼 타입은 그대로 `String`. 허용값만 API에서 `쉬움` / `보통` / `어려움`으로 바꾼다.

### story_scenes
| 변경 | 내용 |
|------|------|
| + `scene_type` | `String` NOT NULL, `narration` / `dialogue` |
| + `content_key` | `String`, nullable |
| + `character_key` | `String`, nullable — `ch_banggui_daughter_in_law` |
| + `mission_condition` | `Text`, nullable |
| + `mission_examples` | `ARRAY(String)`, nullable |
| nullable | `scene_description`, `character_name`, `character_opening`, `character_closing`, `scene_goal`, `required_elements`, `max_turns` |
| nullable (사용 안 함) | `conflict`, `preferred_turns` |

`character_name`은 표시 이름이다. 내레이션 씬은 null.

`required_elements`는 콘텐츠에 들어 있지만 이번 AI 계약에 인자가 없어 **저장만 하고 런타임에 쓰지 않는다.** 씬 종료는 `check_end_condition` + `max_turns`.

### utterance_analyses
| 변경 | 내용 |
|------|------|
| `child_intent` | nullable |
| `detected_elements` | nullable (기본값 없음, 비워 둠) |

`utterance_validity`: `valid` / `invalid`. 씬 완료 플러시 때 Redis에 쌓인 아이 발화마다 1행.

### story_sessions
컬럼 삭제 없음. 이번 구현이 쓰는 것:

- `current_scene_id`, `current_child_turn_count`
- `scene_goal_met`, `scene_end_reason` (`goal_met` / `max_turns`)
- `status` (`in_progress` / `completed`)

쓰지 않는 것 (`accumulated_elements` 등)은 기본값 유지.

---

## AI 계약

`app/domain/progress/ai.py`. 시그니처는 AI팀이 준 그대로. 서버는 Protocol 뒤로만 호출한다.

```python
class StoryAI(Protocol):
    def do_stt(self, m4a_file: BinaryIO, main_description: str) -> str: ...
    def check_correct_chat(
        self, main_description: str, scene_description: str,
        chat_history: ChatHistory, turn: int, text: str,
    ) -> bool: ...
    def check_mission_condition(
        self, chat_history: ChatHistory, mission_condition: str,
    ) -> bool: ...
    def check_end_condition(
        self, scene_goal: str, chat_history: ChatHistory, turn: int,
    ) -> bool: ...
    def make_chat(
        self, chat_history: ChatHistory, main_description: str,
        scene_description: str, scene_goal: str, turn: int,
    ) -> str: ...
```

`make_report`는 Protocol에 넣지 않는다. Phase 6.

동기 함수이므로 서비스에서 `asyncio.to_thread(...)`로 감싼다.

### chat_history

```json
{
  "turns": [
    {"speaker": "character", "text": "ㅇㅇ아, 내 방귀가..."},
    {"speaker": "child", "text": "창피했을 것 같아"}
  ]
}
```

검증 실패한 발화는 넣지 않는다.

### StubStoryAI

| 함수 | 동작 |
|------|------|
| `do_stt` | `"(음성 인식 대기 중)"` 반환. 파일이 비어 있으면 빈 문자열 |
| `check_correct_chat` | 텍스트가 비어 있지 않으면 True |
| `check_mission_condition` | 아이 발화가 1개 이상이면 True |
| `check_end_condition` | `turn >= max_turns`는 서버가 먼저 보고, 스텁은 False |
| `make_chat` | `"그래, 조금 더 말해 줄래?"` |

`ANTHROPIC_API_KEY` 같은 스위치는 두지 않는다. 실제 모듈이 들어오면 `get_story_ai()` 한 곳만 갈아끼운다.

---

## Redis

| 키 | 값 | TTL |
|----|----|-----|
| `conv:{session_id}:{scene_id}` | `{turns, invalid_streak, mission_shown}` JSON | 24시간 |
| `recommended:child:{child_id}` | (기존) 시작 시 삭제 | — |

씬 완료 또는 세션 완료 시 conv 키 삭제. 앱이 중간에 죽으면 그 대화 씬의 Redis 내용은 유실되고, 이어하기 시 해당 씬은 opening부터 다시 시작한다. 이미 complete된 씬의 `messages`는 남아 있다.

---

## API

공통: `CurrentUser` + `child_id` 쿼리. 소유권 실패는 `ForbiddenError("해당 자녀 프로필에 접근할 수 없습니다.")`.

라우트는 `/progress/active`를 `/{story_id}`보다 먼저 선언.

### POST /progress/{story_id}/start?child_id=

- published 스토리만.
- 이 아이의 `in_progress` 세션이 **같은 스토리**면 그대로 반환 (이어하기).
- **다른 스토리**면 `409 ConflictError("이미 진행 중인 이야기가 있습니다.")`.
- 없으면 세션 생성, `current_scene_id` = `scene_order=1`, `recommended:child:{child_id}` 삭제.

```json
{
  "session_id": "uuid",
  "story_id": "uuid",
  "status": "in_progress",
  "current_step": 1,
  "scene_count": 9,
  "step": { "...StepResponse..." }
}
```

start 응답에 1번 스텝을 같이 준다. 프론트가 바로 그리지 않고 `POST .../steps/1`을 한 번 더 불러도 멱등이다.

### GET /progress/active?child_id=

없으면 `null` (200). 있으면:

```json
{
  "session_id": "uuid",
  "story_id": "uuid",
  "title": "방귀 뀌는 며느리",
  "thumbnail_url": "...",
  "current_step": 3,
  "scene_count": 9
}
```

### GET /progress/{story_id}?child_id=

이 스토리의 최신 세션. 없으면 404.

```json
{
  "session_id": "uuid",
  "status": "in_progress",
  "current_step": 3,
  "scene_count": 9,
  "current_kind": "dialogue",
  "turn": 1,
  "max_turns": 4
}
```

### POST /progress/{story_id}/steps/{step_index}?child_id=

`step_index`는 1-based `scene_order`.

허용: 현재 스텝 재진입, 또는 직전 스텝이 끝난 뒤의 다음 스텝. 그 외는 `409`.

- 현재 씬이 대화이고 Redis에 미플러시 대화가 있으면 같은 스텝만 허용 (건너뛰기 금지).
- 진입 시 `current_scene_id` 갱신. 새 대화 씬이면 Redis에 opening을 turn 0으로 넣고 `current_child_turn_count = 0`.

```json
{
  "step_index": 3,
  "scene_count": 9,
  "kind": "dialogue",
  "scene_id": "uuid",
  "scene_description": null,
  "image_url": "https://...",
  "character_name": "며느리",
  "character_opening": "지오야, 내 방귀가 너무 크다는 걸 알면...",
  "character_closing": null,
  "max_turns": 4,
  "turn": 0,
  "mission": null
}
```

내레이션이면 `character_*` / `max_turns` / `turn`은 null. 미션 씬이어도 이 시점의 `mission`은 null이다. 미션은 첫 유효 발화 이후 speak 응답으로 나온다.

이름 치환은 이 응답에서 적용한다.

### POST /progress/{story_id}/steps/{step_index}/speak?child_id=

`multipart/form-data`, 필드 `audio` (m4a). 대화/미션 씬만. 내레이션이면 `400`.

서버 처리:

```
do_stt
check_correct_chat
  False → invalid_streak += 1
          streak < 3: 저장 안 함, turn 유지, accepted=false, 되묻는 대사
          streak >= 3: 저장하고 아래로 (막힘 방지)
  True  → Redis에 child 저장, turn += 1, invalid_streak = 0
미션 있고 아직 안 띄웠으면 check_mission_condition
  True  → mission_shown=true, 응답에 mission, make_chat은 이번엔 생략 가능
turn >= max_turns 또는 check_end_condition
  True  → closing 저장, Redis → messages 플러시, scene_goal_met / scene_end_reason 기록
  False → make_chat → Redis에 character 저장, 응답
```

```json
{
  "accepted": true,
  "child_text": "며느리가 창피했을 것 같아",
  "character_line": "그래도 아직은 못 말하겠어...",
  "turn": 1,
  "max_turns": 4,
  "mission": {
    "condition": "높은 배나무의 배를 떨어뜨리기 위해 ...",
    "examples": ["무엇을 사용할 것인지", "..."]
  },
  "scene_ended": false,
  "end_reason": null
}
```

`scene_ended: true`이면 `character_line`은 `character_closing`(치환 후). 프론트는 대사를 보여 준 뒤 `POST .../steps/{n+1}`로 넘어간다. 대화 씬은 speak가 끝날 때 이미 플러시하므로 complete를 다시 부를 필요 없다.

### POST /progress/{story_id}/steps/{step_index}/complete?child_id=

내레이션 전용. 현재 스텝을 끝난 것으로 표시한다. 다음 진입은 `step_index+1`.

대화 씬에서 호출되면: 이미 플러시됐으면 멱등 200. 아직 안 끝났으면 `409` (강제로 건너뛰지 않음).

마지막 씬 complete 또는 마지막 대화 씬 `scene_ended` 시 세션 `status=completed`, `completed_at` 기록.

---

## 대화 씬 루프 (한 씬)

```
POST /steps/{n}     turn=0, opening → Redis 저장
POST /speak         STT → 검증 → 저장 → turn=1
                    미션 있으면 조건 검사 → 미션 노출
POST /speak         (미션 답이거나 일반 턴)
                    검증 → 저장 → turn++
                    check_end_condition 또는 turn>=max
                    반복
                    종료 시 closing 저장, messages 일괄 insert
POST /steps/{n+1}   다음 씬
```

`PATCH complete` 이름 대신 POST를 쓴다. 본문 없는 상태 전이라 PATCH 의미가 약하다.

---

## Phase 4 스키마 수정 (같은 작업에 포함)

`app/domain/story/schema.py`

- `Difficulty = Literal["쉬움", "보통", "어려움"]`
- `SceneItem`: `scene_type`, 대화 필드는 optional. `character_opening` / `closing`은 목록에서 빼지 않되 null 허용

캐시 키 `story:{id}` / `story:{id}:scenes`는 스키마가 바뀌므로 TTL에 맡긴다. 명시적 무효화는 어드민이 아직 없어 생략.

---

## 예외

| 상황 | 예외 | HTTP |
|------|------|------|
| 토큰 없음/만료 | `UnauthorizedError` | 401 |
| 다른 부모의 child_id | `ForbiddenError` | 403 |
| draft / 없는 스토리·스텝 | `NotFoundError` | 404 |
| 다른 스토리 진행 중 start | `ConflictError` | 409 |
| 허용되지 않은 step 진입 | `ConflictError` | 409 |
| 내레이션에 speak | `BadRequestError` | 400 |
| 오디오 없음 / 빈 파일 | `BadRequestError` | 400 |

---

## 데이터 흐름

```
Router → Service
  → Repository (session, scene, child, messages)
  → Redis (conv 컨텍스트)
  → StoryAI (to_thread)
```

도메인 간 직접 참조 없음. 스토리 콘텐츠는 progress repository가 `Story` / `StoryScene`을 직접 읽는다. (vocabulary가 이미 같은 패턴)

---

## 사용자 승인 내용

- AI: Protocol + 스텁, 시그니처는 제공된 bool/str 계약 유지
- 음성: multipart 직접 업로드
- 씬 스키마 마이그레이션 (scene_type, nullable, 미션 컬럼)
- 미션: `story_scenes.mission_condition` / `mission_examples`
- difficulty: 쉬움/보통/어려움
- 대화 저장: Redis 적재 후 씬 종료 시 messages 일괄 저장
- `/progress/active`: progress 도메인에 구현
- 씬 전진: start에 scene_count, 프론트가 index++ 후 다음 스텝 요청
- 스텝 API는 POST (세션 위치 갱신)
- utterance_analyses: validity만 채움
- slug / 캐릭터 / 이름 치환: 위 기본안
