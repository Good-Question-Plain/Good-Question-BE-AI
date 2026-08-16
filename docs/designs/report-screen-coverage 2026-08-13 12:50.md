# 학습 리포트 화면 대응 설계 — 2026-08-13

## 배경

리포트 화면 디자인과 기존 응답을 대조한 결과, 화면에 필요한데 응답에 없는 정보가 있었다.
리포트는 **이야기 학습이 끝난 직후 한 번 생성·저장**되고, 이후 조회는 저장된 값을 그대로 내보낸다.
따라서 화면에 필요한 값은 전부 생성 시점에 만들어 두어야 한다.

## 화면 ↔ 응답 대조

| 화면 요소 | 응답 필드 | 상태 |
|---|---|---|
| 헤더 — 이야기 제목 | `story_title` | 추가 |
| 헤더 — 날짜·시각 | `completed_at` | 기존 |
| 지오의 말하기 특징 | `vocabulary.speech_summary` | 기존 |
| 어휘 탭 — 사용한 주요 어휘 | `vocabulary.used_words` | 기존 |
| 어휘 탭 — 궁금해한 어휘 | `vocabulary.curious_words` | 기존 |
| 어휘 탭 — 자주 사용한 표현 | `vocabulary.expression_patterns` | 기존 |
| 표현 탭 3항목 | `expression[]` | 기존 |
| 논리 탭 2항목 | `logic[]` | 기존 |
| **오늘의 대표 발화** + 선정 이유 | `representative.text` / `.reason` | 기존 |
| **집에서 이어가볼까요?** | `home_conversation` | **신규** |
| 이전 / 다음 리포트 보기 | `previous_story_id` / `next_story_id` | **신규** |
| 아이 이름 (문구에 삽입) | `child_name` | 추가 |

`representative` 가 화면의 "오늘의 대표 발화" 카드다. 리포트는 이야기 1회 학습에 1건이므로
"오늘의"는 그 학습 회차를 가리키는 UI 문구이고, 데이터상으로는 해당 리포트의 대표 발화 1건이다.

## 신규 — 집에서 이어가볼까요?

두 묶음으로 각 3개 질문. 질문마다 어떤 말하기 연습인지 라벨이 붙는다.

```json
"home_conversation": {
  "story_topics": [
    {"question": "며느리는 사람들 앞에서 방귀를 뀌었을 때 어떤 기분이었을까?",
     "practice_label": "감정 표현 연습"}
  ],
  "daily_life": [
    {"question": "너도 창피해서 하고 싶은 말을 하지 못한 적이 있어?",
     "practice_label": "감정 표현 연습"}
  ]
}
```

- `story_topics` — 이야기 속 상황·인물을 더 깊이 파고드는 질문
- `daily_life` — 이야기 주제를 아이의 실제 경험으로 옮겨오는 질문
- 질문은 학부모가 아이에게 그대로 읽어줄 수 있게 아이에게 말 거는 반말로 생성한다.
- 예/아니오로 끝나지 않는 질문을 만들도록 프롬프트에 명시했다.
- `practice_label` 은 자유 문자열. 고정 enum 으로 묶으면 이야기 성격에 안 맞는 라벨이 강제된다.

리포트 본문과 **같은 LLM 호출 1회**에서 함께 생성한다. 호출 수를 늘리지 않는다.

## 이전 / 다음 리포트

같은 아이의 리포트를 `created_at` 순으로 훑어 앞뒤 리포트의 `story_id` 를 내려준다.
클라이언트는 그 값으로 `GET /reports/{story_id}?child_id=` 를 다시 부르면 된다.
끝단이면 `null` 이라 버튼을 비활성화하면 된다.

## DB 변경 (alembic 005)

`learning_reports` 에 JSONB 컬럼 2개 추가.

| 컬럼 | 설명 |
|---|---|
| story_topic_questions | `[{question, practice_label}]` |
| daily_life_questions | `[{question, practice_label}]` |

`representative_score` 는 **추가하지 않았다.** 대표 발화가 리포트당 1건으로 확정되어
여러 리포트를 점수로 비교할 일이 없어졌고, 읽는 곳 없는 컬럼을 남기지 않기 위해서다.

## 변경 파일

```
app/models/report.py                 JSONB 컬럼 2개
alembic/versions/005_...py           신규
app/domain/vocabulary/schema.py      ConversationPrompt, HomeConversationSection,
                                     ReportResponse 에 story_title·child_name·home_conversation·이전/다음
app/domain/vocabulary/analyzer.py    LLM 페이로드·프롬프트에 질문 6개, 스텁 기본 질문
app/domain/vocabulary/repository.py  저장 + get_neighbor_story_ids()
app/domain/vocabulary/service.py     응답 조립
```

## 남은 과제

- 이전/다음 리포트를 `created_at` 순서로 정한다. 같은 이야기를 두 번 학습하면 `story_id` 가 중복돼
  같은 화면으로 이동한다. 이력 탐색이 중요해지면 조회 키를 `report_id` 로 바꾸는 편이 정확하다.
- 실제 API 키로 질문 생성 품질 미검증.
