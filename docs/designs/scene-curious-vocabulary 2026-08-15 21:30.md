# 씬마다 궁금한 단어 선택 — 2026-08-15

## 구현 범위

이야기 진행 중 아이가 해당 씬의 미리 매달린 단어 중 궁금한 것을 고른다.
리포트 어휘 탭의 `curious_words` 와 `GET /vocabulary?kind=curious` 의 출처가 된다.

단어 목록은 단계 진입 응답에 붙인다. 별도 GET 없음.

| Method | Path | 역할 |
|---|---|---|
| POST | `/progress/{story_id}/steps/{step_index}` | 단계 진입. `vocabularies` 에 이 씬 단어 + 선택 여부 |
| POST | `/progress/{story_id}/steps/{step_index}/vocabularies` | 단어 선택 (`scene_vocabulary_id`) |
| DELETE | `/progress/{story_id}/steps/{step_index}/vocabularies/{scene_vocabulary_id}` | 선택 취소 |

## 테이블

### `scene_vocabularies` — 콘텐츠가 씬에 미리 매다는 단어

| 컬럼 | 설명 |
|---|---|
| id | PK |
| scene_id | `story_scenes.id` FK CASCADE |
| word | 표시 단어 |
| definition | 뜻 (선택) |
| example_sentence | 예문 (선택) |

Unique `(scene_id, word)`.

### `child_vocabularies` — 아이가 고른 기록

| 컬럼 | 설명 |
|---|---|
| id | PK |
| child_id | `children.id` FK CASCADE |
| session_id | `story_sessions.id` FK CASCADE |
| scene_vocabulary_id | `scene_vocabularies.id` FK CASCADE |
| kind | `curious` |
| saved_at | 선택 시각 |

Unique `(session_id, scene_vocabulary_id)`. 같은 회차에서 같은 단어는 한 번만.

## 데이터 흐름

```
콘텐츠 시드 → scene_vocabularies
아이 탭 → child_vocabularies
리포트 생성 → child_vocabularies 를 report_vocabularies(kind=curious) 로 스냅샷
GET /vocabulary?kind=curious → child_vocabularies (실시간)
리포트 curious_words → 생성 시점 스냅샷
```

`used` 는 기존처럼 발화에서 LLM 이 추출한다. 씬 FK 를 쓰지 않는다.

## 제약

- 진행 중 세션의 **현재 단계**에서만 선택/취소한다.
- 이미 고른 단어를 다시 POST 하면 그대로 성공(멱등).
- 단어가 해당 씬에 없으면 404.
