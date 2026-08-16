# 대표 발화 선정 설계 — 2026-08-12

## 구현 범위

학습 리포트에 "이번 이야기에서 가장 잘 말한 발화" 하나를 뽑아 선정 이유와 함께 노출한다.

## 방식 — 하이브리드 (규칙 + LLM)

| 단계 | 담당 | 이유 |
|---|---|---|
| 1. 점수 계산 → 최고점 발화 선정 | 규칙 (순수 함수) | 결정론적, 무료, 재현 가능 |
| 2. 선정 이유 한 문장 생성 | 분석기(LLM) | 자연스러운 톤 |

- 규칙만 쓰면 선정 이유 문장이 부자연스럽다.
- LLM만 쓰면 비싸고 비결정론적이다.
- 점수는 안정적으로 두고 문장만 LLM에 맡기면 호출 비용이 발화 1건 수준(~$0.001)으로 떨어진다.

선정 로직은 분석기 구현 바깥의 모듈 함수라, 스텁을 실제 LLM 구현체로 바꿔도 **선정 결과는 그대로 재현된다.**

## 1단계 — 점수 규칙

입력은 `utterance_analyses.detected_elements` 의 사고 요소 태그.

| 조건 | 점수 |
|---|---|
| 태그 3가지 이상 | +3 |
| 태그 2가지 이상 | +2 |
| EMOTION + REASON | +3 |
| PERSPECTIVE + EMPATHY | +3 |
| DECISION + REQUEST | +3 |
| DECISION + SOLUTION | +3 |
| 길이 20~100자 | +1 |
| 길이 10자 미만 | -2 |

- **태그 개수 점수는 배타적**: 3가지 이상이면 +3만 적용하고 +2는 더하지 않는다.
- **조합 보너스는 누적**: 여러 조합을 동시에 만족하면 모두 더한다.
- **최소 점수 3점**: 최고점이 3점에 못 미치면 대표 발화를 뽑지 않는다(`representative: null`).
  "네", "몰라요" 같은 짧은 대답만 오간 세션에서 민망한 발화가 대표로 노출되는 것을 막는다.

검증 예시 — `"며느리가 속상했을 것 같아. 시아버지가 먼저 미안하다고 해야 해."`
(EMOTION, REASON, DECISION, SOLUTION / 34자) → 3 + 3 + 3 + 1 = **10점**

## 2단계 — 동점 처리

1. DECISION 또는 SOLUTION 포함 발화 우선
2. 씬 순서가 뒤인 발화
3. 발화(턴) 순서가 뒤인 발화

## 3단계 — 선정 이유 문장

선정된 발화의 텍스트와 태그를 분석기에 넘겨 자연어 한 문장을 만든다.

```
입력: "며느리가 속상했을 것 같아. 시아버지가 먼저 미안하다고 해야 해."
      [EMOTION, REASON, DECISION, SOLUTION]
출력: "인물의 감정을 짐작하고, 관계 회복을 위한 자신의 판단을 자연스럽게 연결해서 말했어요."
```

현재는 LLM 미연동 상태라 스텁이 태그 조합별 템플릿 문구를 조립한다.
`describe_selection()` 은 LLM 구현체에서도 호출 실패 시 폴백으로 쓸 수 있다.

## 결정 사항 (사용자 승인)

- `utterance_analyses.detected_elements` 구조를 **객체 배열**로 확정
  `[{"element": "EMOTION", "evidence": "속상했을 것 같아"}]`
  → Phase 5 발화 분석이 지켜야 할 계약. 태그만 필요한 곳은 `element` 키만 뽑아 쓴다.
- 대표 발화는 **리포트(세션)당 1개**
- 태그 개수 점수는 **배타적**
- 최소 점수 **3점** 미만이면 대표 발화 없음

## DB 변경 (alembic 004)

`learning_reports` 에 컬럼 추가.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| representative_message_id | UUID FK NULL | `messages.id`, ON DELETE SET NULL |
| representative_quote | TEXT NULL | 선정된 발화 원문 |
| representative_reason | TEXT NULL | 선정 이유 한 문장 |
| representative_elements | TEXT[] | 선정 근거가 된 태그 |

## 변경 파일

```
app/domain/vocabulary/analyzer.py    score_utterance / select_representative / describe_selection
                                     UtteranceInput 에 message_id·turn_order·elements 추가
                                     ReportDraft 에 representative 추가
app/domain/vocabulary/schema.py      RepresentativeUtterance, ReportResponse.representative
app/domain/vocabulary/service.py     detected_elements → 태그 파싱, 응답 매핑
app/domain/vocabulary/repository.py  save_result / reset_to_generating 에 대표 발화 반영
app/models/report.py                 컬럼 4개 추가
alembic/versions/004_...py           신규
```

## 남은 과제

- 임계값 3점은 실데이터 없이 정한 값이다. 대표 발화가 비는 비율을 보고 조정한다
  (`analyzer._MIN_REPRESENTATIVE_SCORE`).
- 대표 발화가 없을 때 리포트 화면에서 무엇을 보여줄지 프론트와 합의 필요.
- 실제 LLM 분석기 구현 시 `describe_selection` 을 폴백으로 두고 프롬프트를 붙인다.
