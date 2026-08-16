# 실제 LLM 리포트 분석기 설계 — 2026-08-13

## 구현 범위

Phase 6 마지막 항목. 스텁으로 두었던 `get_report_analyzer()` 를 Anthropic 기반 구현체로 교체한다.

## 호출 구조

리포트 1건 = **API 호출 1회**. 어휘 총평, 표현 3항목, 논리 2항목, 대표 발화 선정 이유를
한 번의 응답으로 함께 받는다. 항목마다 나눠 부르면 호출 수가 6배가 되고 톤도 제각각이 된다.

대표 발화 **선정 자체는 여전히 규칙**(`select_representative`)이 담당한다.
LLM 은 이미 선정된 발화를 받아 이유 문장만 쓴다 — 하이브리드 설계 유지.

```
run_generation
  → select_representative(발화들)          # 규칙, 결정론적
  → messages.parse(output_format=...)      # LLM 1회
  → 라벨·설명 부착 + 인용문 검증
  → ReportDraft
```

## 구조화 출력

`anthropic` SDK 의 `messages.parse(output_format=PydanticModel)` 를 사용한다
(`output_config.format` 의 JSON Schema 구조화 출력을 SDK 가 대신 처리).
자유 텍스트 JSON 을 파싱하는 방식과 달리 스키마 위반 응답 자체가 나오지 않는다.

`LLMReportPayload` 에는 **LLM 이 생각해야 하는 값만** 담는다.
항목 라벨("관점과 공감")과 설명 문구는 PRD 고정값이므로 서버가 붙인다. 토큰도 아끼고 문구도 흔들리지 않는다.

| 필드 | 내용 |
|---|---|
| speech_summary | 말하기 특징 2~3문장 |
| vocabulary_feedback | 어휘 총평 2~3문장 |
| expression_patterns | 반복 표현 패턴 (최대 3개로 절단) |
| vocabularies | word / kind(used·curious) / definition / example_sentence (최대 10개로 절단) |
| expression_items | key(enum 3종) / quotes / strength / tip |
| logic_items | key(enum 2종) / quotes / strength / tip |
| representative_reason | 대표 발화 선정 이유 한 문장 |

`key` 는 enum 이라 모르는 항목이 오면 API 단계에서 막힌다.

## 인용문 검증

PRD 는 "아이가 실제 말한 발화 예시를 인용"하도록 요구한다.
프롬프트로 원문 인용을 지시하되, 응답의 `quotes` 를 **실제 발화 집합과 대조해 일치하지 않는 항목은 버린다.**
지어낸 인용문이 학부모 화면에 노출되는 것을 코드 레벨에서 차단한다.

## 실패 처리

LLM 호출 실패나 스키마 해석 실패는 예외로 던진다.
`ReportService.run_generation` 이 이를 잡아 `status=failed` + `failure_reason` 으로 기록하고,
`POST /reports/{story_id}/generate` 재호출 시 재시도된다.

스텁으로 조용히 대체하지 않는다. 품질 낮은 리포트가 정상인 척 남는 것보다 실패가 드러나는 편이 낫다.

## 설정

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| ANTHROPIC_API_KEY | (빈 값) | **비어 있으면 스텁 분석기로 동작** — 로컬 개발·테스트용 |
| ANTHROPIC_MODEL | claude-sonnet-4-6 | 리포트 품질/비용 균형. 비용을 더 줄이려면 claude-haiku-4-5 |
| ANTHROPIC_MAX_TOKENS | 2000 | 리포트 1건 분량 |
| ANTHROPIC_TIMEOUT_SECONDS | 60 | 백그라운드 작업이라 여유 있게 |

`temperature=0.3` — 리포트 톤이 매번 크게 흔들리지 않도록 낮게 고정.

## 변경 파일

```
app/core/config.py                   ANTHROPIC_* 설정 4개
app/core/llm.py                      신규 — AsyncAnthropic 싱글턴, is_llm_configured()
app/domain/vocabulary/analyzer.py    LLMReportPayload, LLMReportAnalyzer, 프롬프트,
                                     get_report_analyzer() 분기
.env.example                         ANTHROPIC_* 항목
```

## 남은 과제

- 실제 API 키로 end-to-end 호출 미검증 (키 없이 스텁 경로와 매핑 로직만 확인).
- 프롬프트는 실제 아이 발화 데이터를 보고 다듬어야 한다. 특히 tip 문구가 상투적으로 나올 가능성.
- 비용 관측치 없음. 운영 후 토큰 사용량 확인하고 모델·max_tokens 조정.
