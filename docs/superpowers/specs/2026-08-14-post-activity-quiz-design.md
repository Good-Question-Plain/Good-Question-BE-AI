# Post-Activity Quiz Design

## 개요

스토리 세션이 완료된 후 진행되는 활동 단계. 씬 순서 맞추기 퀴즈 → 핵심 단어 확인 → 리텔링(retelling) → 완성 화면 순으로 진행된다.

## 기능 흐름

```
세션 완료(status="completed")
  → GET /sessions/{session_id}/post-activity
      카드 셔플 반환 (scene_title, image_url)
  → POST /sessions/{session_id}/post-activity/submit
      submitted_order 검증 → is_order_correct 저장
      오답: attempt_count++ 반환 (정답 미제공)
      정답: vocabulary 목록 함께 반환
  → POST /sessions/{session_id}/post-activity/retell
      retelling_text 저장, completed_at 설정
      완성 화면 데이터 반환 (story_title, utterance_count, new_vocabulary_count)
```

## DB 변경

### StoryScene — scene_title 컬럼 추가

```
scene_title: VARCHAR NOT NULL
```

퀴즈 카드에 표시할 짧은 씬 제목. `scene_description`(긴 설명)과 분리.

### 마이그레이션

- `008_add_scene_title_to_story_scenes.py` — scene_title 컬럼 추가
- `009_seed_mock_story_three_little_pigs.py` — 아기돼지 삼형제 mock 데이터 삽입

## 도메인 구조

```
app/domain/post_activity/
├── __init__.py
├── router.py      prefix: /sessions
├── schema.py
├── service.py
└── repository.py
```

## API 명세

### GET /sessions/{session_id}/post-activity

인가: `session.child.parent_id == current_user.id`

전제: `session.status == "completed"` (아니면 400)

`PostActivityResult`가 없으면 생성 (attempt_count=0).
씬을 scene_order로 정렬한 뒤 서버 사이드 셔플해서 반환.

**Response 200:**
```json
{
  "attempt_count": 0,
  "is_completed": false,
  "cards": [
    {"scene_id": "uuid", "title": "튼튼한 벽돌집", "image_url": null}
  ]
}
```

### POST /sessions/{session_id}/post-activity/submit

**Body:**
```json
{"submitted_order": ["uuid", "uuid", "uuid", "uuid", "uuid"]}
```

- `PostActivityResult.is_order_correct`가 이미 `true`이면 400 (이미 정답 처리됨)
- `submitted_order`의 scene_id 수 != 전체 씬 수이면 400
- 정답 판정: `submitted_order`를 DB의 `scene_order` 오름차순과 비교
- `attempt_count` +1, `is_order_correct` 저장

**Response 200 (오답):**
```json
{"is_correct": false, "attempt_count": 2}
```

**Response 200 (정답):**
```json
{
  "is_correct": true,
  "attempt_count": 1,
  "vocabulary": [
    {"word": "용감한", "definition": "두렵거나 힘들어도 포기하지 않고 맞서는"}
  ]
}
```

### POST /sessions/{session_id}/post-activity/retell

전제: `PostActivityResult.is_order_correct == true` (아니면 400)

STT 결과 텍스트는 호출 전 외부(프론트/다른 레이어)에서 처리해서 넘겨줌.

발화 횟수 · 새로 배운 단어 수는 stub 함수(`count_child_utterances`, `count_story_vocabulary`)로 분리해서 서비스 외부에서 주입받는 구조로 작성.

**Body:**
```json
{"retelling_text": "옛날에 아기돼지 세 마리가..."}
```

**Response 200:**
```json
{
  "story_title": "아기돼지 삼형제",
  "utterance_count": 8,
  "new_vocabulary_count": 4
}
```

## Mock 데이터 (아기돼지 삼형제)

| scene_order | scene_title |
|-------------|-------------|
| 1 | 가벼운 지푸라기집 |
| 2 | 나무로 만든 집 |
| 3 | 튼튼한 벽돌집 |
| 4 | 늑대가 찾아왔어요 |
| 5 | 셋이 함께 안전해요 |

핵심 단어: 용감한, 친구, 숲, 모험 (각각 씬 1~4에 배치)

## 인가 흐름

```
CurrentUser (Parent)
  → StorySession 조회
  → session.child.parent_id != parent.id → 403
  → session 없음 → 404
```
