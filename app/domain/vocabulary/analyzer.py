"""학습 리포트 분석기.

인터페이스만 확정하고 현재는 스텁 구현을 사용한다.
실제 LLM 연동 시 `LLMReportAnalyzer` 를 추가하고 `get_report_analyzer()` 가 그것을 반환하도록 바꾼다.
"""

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm import get_anthropic_client, is_llm_configured
from app.domain.vocabulary.schema import ConversationPrompt, ReportFeedbackItem, VocabularyKind

# PRD 3.6 분석 항목 정의
EXPRESSION_CRITERIA: tuple[tuple[str, str, str], ...] = (
    ("perspective_empathy", "관점과 공감", "다른 사람의 감정을 짐작하고 공감하는 표현"),
    ("emotion_expression", "감정 표현", "감정을 나타내는 다양한 어휘 사용"),
    ("interaction", "상호작용", "캐릭터의 질문에 자기 생각을 대답하는 반응"),
)

LOGIC_CRITERIA: tuple[tuple[str, str, str], ...] = (
    ("thought_reason", "생각과 이유", "자신의 생각과 그 근거를 함께 말하는 능력"),
    ("outcome_solution", "결과와 해결", "문제 상황 파악 및 해결 방향 제시"),
)

ExpressionKey = Literal["perspective_empathy", "emotion_expression", "interaction"]
LogicKey = Literal["thought_reason", "outcome_solution"]

_CRITERIA_BY_KEY: dict[str, tuple[str, str]] = {
    key: (label, description) for key, label, description in EXPRESSION_CRITERIA + LOGIC_CRITERIA
}

# 사고 요소 태그 (utterance_analyses.detected_elements)
EMOTION = "EMOTION"
REASON = "REASON"
PERSPECTIVE = "PERSPECTIVE"
EMPATHY = "EMPATHY"
DECISION = "DECISION"
REQUEST = "REQUEST"
SOLUTION = "SOLUTION"

# 대표 발화 점수 규칙 — 태그 조합 보너스는 서로 누적된다
_COMBO_BONUS: tuple[tuple[frozenset[str], int], ...] = (
    (frozenset({EMOTION, REASON}), 3),
    (frozenset({PERSPECTIVE, EMPATHY}), 3),
    (frozenset({DECISION, REQUEST}), 3),
    (frozenset({DECISION, SOLUTION}), 3),
)

# 태그 개수 점수는 배타적 — 상위 조건 하나만 적용
_TAG_COUNT_BONUS: tuple[tuple[int, int], ...] = ((3, 3), (2, 2))

_IDEAL_LENGTH = range(20, 101)
_IDEAL_LENGTH_BONUS = 1
_TOO_SHORT_LENGTH = 10
_TOO_SHORT_PENALTY = -2

# 동점 시 우선하는 태그
_TIEBREAK_TAGS = frozenset({DECISION, SOLUTION})

# 이 점수에 못 미치면 대표 발화를 뽑지 않는다.
# 짧은 대답만 오간 세션에서 "네." 같은 발화가 대표로 노출되는 것을 막는다.
_MIN_REPRESENTATIVE_SCORE = 3

_COMBO_REASONS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({EMOTION, REASON}),
        "인물의 감정을 짐작하고 그렇게 생각한 이유까지 함께 말했어요.",
    ),
    (
        frozenset({PERSPECTIVE, EMPATHY}),
        "다른 사람의 입장에서 마음을 헤아려 말했어요.",
    ),
    (
        frozenset({DECISION, REQUEST}),
        "자신의 판단을 세우고 필요한 것을 분명하게 요청했어요.",
    ),
    (
        frozenset({DECISION, SOLUTION}),
        "문제 상황에 대한 판단과 해결 방향을 연결해서 말했어요.",
    ),
)

_ELEMENT_LABELS: dict[str, str] = {
    EMOTION: "감정",
    REASON: "이유",
    PERSPECTIVE: "관점",
    EMPATHY: "공감",
    DECISION: "판단",
    REQUEST: "요청",
    SOLUTION: "해결",
}

_STOPWORDS = frozenset(
    {
        "그리고", "그래서", "하지만", "그런데", "그러면", "그거", "저거", "이거",
        "우리", "너무", "정말", "진짜", "그냥", "아마", "만약", "때문",
    }
)

_TOKEN_SPLIT = re.compile(r"[^0-9A-Za-z가-힣]+")

_MAX_WORDS = 10
_MAX_PATTERNS = 3
_MAX_QUOTES_PER_ITEM = 2
_MAX_QUESTIONS_PER_GROUP = 3


@dataclass(slots=True)
class UtteranceInput:
    message_id: uuid.UUID
    text: str
    scene_order: int
    turn_order: int
    elements: list[str] = field(default_factory=list)
    child_intent: str | None = None
    main_point: str | None = None
    utterance_validity: str | None = None


@dataclass(slots=True)
class ReportContext:
    story_title: str
    child_name: str
    utterances: list[UtteranceInput] = field(default_factory=list)


@dataclass(slots=True)
class DraftVocabulary:
    word: str
    kind: VocabularyKind
    definition: str | None = None
    example_sentence: str | None = None


@dataclass(slots=True)
class RepresentativeDraft:
    message_id: uuid.UUID
    text: str
    elements: list[str]
    reason: str


@dataclass(slots=True)
class ReportDraft:
    speech_summary: str
    vocabulary_feedback: str
    expression_patterns: list[str]
    expression_items: list[ReportFeedbackItem]
    logic_items: list[ReportFeedbackItem]
    vocabularies: list[DraftVocabulary]
    analyzer_name: str
    report_version: str
    representative: RepresentativeDraft | None = None
    story_topic_questions: list[ConversationPrompt] = field(default_factory=list)
    daily_life_questions: list[ConversationPrompt] = field(default_factory=list)


def score_utterance(utterance: UtteranceInput) -> int:
    """대표 발화 점수. 결정론적이며 분석기 구현과 무관하다."""
    tags = set(utterance.elements)
    score = 0

    for threshold, bonus in _TAG_COUNT_BONUS:
        if len(tags) >= threshold:
            score += bonus
            break

    for combo, bonus in _COMBO_BONUS:
        if combo <= tags:
            score += bonus

    length = len(utterance.text.strip())
    if length in _IDEAL_LENGTH:
        score += _IDEAL_LENGTH_BONUS
    elif length < _TOO_SHORT_LENGTH:
        score += _TOO_SHORT_PENALTY

    return score


def select_representative(utterances: list[UtteranceInput]) -> UtteranceInput | None:
    """최고점 발화를 고른다. 동점이면 DECISION/SOLUTION 포함 → 늦은 씬 → 늦은 턴 순.

    최고점이 `_MIN_REPRESENTATIVE_SCORE` 에 못 미치면 아무것도 뽑지 않는다.
    """
    candidates = [u for u in utterances if u.text.strip()]
    if not candidates:
        return None

    def rank(utterance: UtteranceInput) -> tuple[int, int, int, int]:
        return (
            score_utterance(utterance),
            int(bool(_TIEBREAK_TAGS & set(utterance.elements))),
            utterance.scene_order,
            utterance.turn_order,
        )

    best = max(candidates, key=rank)
    return best if score_utterance(best) >= _MIN_REPRESENTATIVE_SCORE else None


def describe_selection(utterance: UtteranceInput) -> str:
    """LLM 없이 태그 조합만으로 선정 이유를 조립한다 (스텁·폴백용)."""
    tags = set(utterance.elements)
    matched = [sentence for combo, sentence in _COMBO_REASONS if combo <= tags]
    if matched:
        return " ".join(matched)

    labels = [_ELEMENT_LABELS[tag] for tag in _ELEMENT_LABELS if tag in tags]
    if labels:
        joined = "·".join(labels)
        return f"{joined}{_object_particle(joined)} 담아 자기 생각을 말했어요."
    return "자기 생각을 문장으로 이어서 말했어요."


def _object_particle(word: str) -> str:
    """받침 유무에 따라 목적격 조사를 고른다."""
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return "를"
    return "을" if (ord(last) - 0xAC00) % 28 else "를"


class ReportAnalyzer(Protocol):
    async def analyze(self, context: ReportContext) -> ReportDraft: ...


class StubReportAnalyzer:
    """LLM 연동 전 임시 분석기.

    실제 발화에서 인용문과 빈출 어휘를 추출해 리포트 골격을 채운다.
    잘한 점·개선 팁 등 판단이 필요한 문구는 분석 대기 상태임을 명시한다.
    """

    name = "stub"
    version = "stub_v1"

    async def analyze(self, context: ReportContext) -> ReportDraft:
        texts = [u.text.strip() for u in context.utterances if u.text.strip()]
        tokens = self._tokenize(texts)

        words = self._frequent_words(tokens)
        patterns = self._frequent_patterns(tokens)

        return ReportDraft(
            speech_summary=self._speech_summary(context, texts),
            vocabulary_feedback=(
                "AI 어휘 분석은 준비 중입니다. 지금은 아이가 실제로 사용한 어휘만 정리해 보여드려요."
            ),
            expression_patterns=patterns,
            expression_items=self._build_items(EXPRESSION_CRITERIA, texts),
            logic_items=self._build_items(LOGIC_CRITERIA, texts),
            vocabularies=[DraftVocabulary(word=w, kind="used") for w in words],
            analyzer_name=self.name,
            report_version=self.version,
            representative=self._representative(context.utterances),
            story_topic_questions=self._story_topic_questions(context),
            daily_life_questions=self._daily_life_questions(),
        )

    @staticmethod
    def _story_topic_questions(context: ReportContext) -> list[ConversationPrompt]:
        return [
            ConversationPrompt(
                question=f"「{context.story_title}」에서 가장 기억에 남는 장면은 어디였어?",
                practice_label="이야기 되짚기 연습",
            ),
            ConversationPrompt(
                question="그때 그 인물은 어떤 마음이었을까?",
                practice_label="감정 표현 연습",
            ),
            ConversationPrompt(
                question="네가 그 인물이었다면 어떻게 했을 것 같아?",
                practice_label="관점과 공감 연습",
            ),
        ]

    @staticmethod
    def _daily_life_questions() -> list[ConversationPrompt]:
        return [
            ConversationPrompt(
                question="오늘 하루 중에 비슷한 기분이 들었던 일이 있었어?",
                practice_label="일상 연결 연습",
            ),
            ConversationPrompt(
                question="그럴 때 어떻게 하면 좋았을 것 같아?",
                practice_label="결과와 해결 연습",
            ),
            ConversationPrompt(
                question="친구가 같은 일을 겪는다면 어떤 말을 해주고 싶어?",
                practice_label="관점과 공감 연습",
            ),
        ]

    @staticmethod
    def _representative(utterances: list[UtteranceInput]) -> RepresentativeDraft | None:
        """선정은 공통 규칙, 이유 문장만 분석기가 만든다. 실제 LLM 구현체에서 이 부분을 교체한다."""
        selected = select_representative(utterances)
        if selected is None:
            return None
        return RepresentativeDraft(
            message_id=selected.message_id,
            text=selected.text.strip(),
            elements=list(selected.elements),
            reason=describe_selection(selected),
        )

    @staticmethod
    def _tokenize(texts: list[str]) -> list[list[str]]:
        return [
            [t for t in _TOKEN_SPLIT.split(text) if len(t) >= 2 and t not in _STOPWORDS]
            for text in texts
        ]

    @staticmethod
    def _frequent_words(tokens: list[list[str]]) -> list[str]:
        counter = Counter(token for line in tokens for token in line)
        return [word for word, _ in counter.most_common(_MAX_WORDS)]

    @staticmethod
    def _frequent_patterns(tokens: list[list[str]]) -> list[str]:
        counter: Counter[str] = Counter()
        for line in tokens:
            counter.update(f"{a} {b}" for a, b in zip(line, line[1:]))
        return [phrase for phrase, count in counter.most_common(_MAX_PATTERNS) if count >= 2]

    @staticmethod
    def _speech_summary(context: ReportContext, texts: list[str]) -> str:
        if not texts:
            return f"{context.child_name}(이)가 「{context.story_title}」에서 남긴 발화가 없어요."
        return (
            f"{context.child_name}(이)는 「{context.story_title}」에서 총 {len(texts)}번 이야기했어요. "
            "자세한 말하기 특징 분석은 준비 중입니다."
        )

    @staticmethod
    def _build_items(
        criteria: tuple[tuple[str, str, str], ...],
        texts: list[str],
    ) -> list[ReportFeedbackItem]:
        """발화를 항목 수만큼 라운드로빈으로 나눠 인용문으로 붙인다."""
        return [
            ReportFeedbackItem(
                key=key,
                label=label,
                description=description,
                quotes=texts[index :: len(criteria)][:_MAX_QUOTES_PER_ITEM],
            )
            for index, (key, label, description) in enumerate(criteria)
        ]


class LLMExpressionItem(BaseModel):
    key: ExpressionKey = Field(description="분석 항목 식별자")
    quotes: list[str] = Field(description="아이가 실제로 말한 문장 원문 인용. 최대 2개, 없으면 빈 배열")
    strength: str = Field(description="이 항목에서 잘한 점 한 문장")
    tip: str = Field(description="다음에 해보면 좋을 점 한 문장")


class LLMLogicItem(BaseModel):
    key: LogicKey = Field(description="분석 항목 식별자")
    quotes: list[str] = Field(description="아이가 실제로 말한 문장 원문 인용. 최대 2개, 없으면 빈 배열")
    strength: str = Field(description="이 항목에서 잘한 점 한 문장")
    tip: str = Field(description="다음에 해보면 좋을 점 한 문장")


class LLMVocabularyWord(BaseModel):
    word: str = Field(description="어휘 한 낱말")
    kind: VocabularyKind = Field(description="used=아이가 사용한 어휘, curious=아이가 뜻을 궁금해한 어휘")
    definition: str = Field(description="초등학생이 이해할 수 있는 짧은 뜻풀이")
    example_sentence: str = Field(description="그 어휘를 쓴 짧은 예문")


class LLMConversationPrompt(BaseModel):
    question: str = Field(description="학부모가 아이에게 그대로 읽어줄 수 있는 질문 한 문장")
    practice_label: str = Field(
        description="이 질문이 어떤 말하기 연습인지 6자 안팎의 짧은 라벨. 예: 감정 표현 연습"
    )


class LLMReportPayload(BaseModel):
    """LLM 이 채워야 할 리포트 본문. 라벨·설명 등 고정값은 서버가 붙인다."""

    speech_summary: str = Field(description="아이의 말하기 특징을 2~3문장으로 요약")
    vocabulary_feedback: str = Field(description="어휘 사용에 대한 총평 2~3문장")
    expression_patterns: list[str] = Field(description="아이가 반복해서 쓴 표현 패턴, 최대 3개")
    vocabularies: list[LLMVocabularyWord] = Field(description="주요 어휘, 최대 10개")
    expression_items: list[LLMExpressionItem] = Field(description="표현 영역 3개 항목 모두")
    logic_items: list[LLMLogicItem] = Field(description="논리 영역 2개 항목 모두")
    representative_reason: str = Field(
        description="대표 발화를 왜 잘 말했다고 보는지 한 문장. 대표 발화가 없으면 빈 문자열"
    )
    story_topic_questions: list[LLMConversationPrompt] = Field(
        description="이야기 속 상황을 더 깊이 이야기해볼 질문 3개"
    )
    daily_life_questions: list[LLMConversationPrompt] = Field(
        description="이야기를 아이의 일상 경험과 연결해볼 질문 3개"
    )


_SYSTEM_PROMPT = """너는 초등학생의 말하기 발달을 분석하는 교육 전문가다.
아이가 이야기 속 인물과 나눈 대화를 읽고, 학부모가 읽을 학습 리포트를 작성한다.

규칙:
- 모든 문장은 한국어 존댓말로, 학부모에게 이야기하듯 따뜻하고 구체적으로 쓴다.
- quotes 에는 아이가 실제로 말한 문장을 토씨 하나 바꾸지 말고 그대로 옮긴다. 절대 지어내지 않는다.
- 해당하는 발화가 없는 항목은 quotes 를 빈 배열로 두고, 관찰된 사실만 담백하게 적는다.
- strength 는 잘한 점, tip 은 다음에 해보면 좋을 점을 각각 한 문장으로 쓴다.
- 아이를 평가하거나 부족하다고 단정하지 않는다. 성장 가능성을 중심으로 쓴다.
- 표현 영역 3개 항목과 논리 영역 2개 항목을 빠짐없이 채운다.

집에서 이어갈 대화 질문:
- story_topic_questions 는 이야기 속 상황·인물을 더 깊이 파고드는 질문 3개.
- daily_life_questions 는 이야기 주제를 아이의 실제 경험으로 옮겨오는 질문 3개.
- 질문은 학부모가 아이에게 그대로 읽어줄 수 있게 아이에게 말 거는 반말로 쓴다.
- 예/아니오로 끝나지 않고 아이가 이유나 상황을 이야기하게 되는 질문으로 만든다."""


class LLMReportAnalyzer:
    """Anthropic 기반 분석기.

    대표 발화 선정은 규칙(`select_representative`)이 담당하고, LLM 은 리포트 문장만 만든다.
    """

    name = "anthropic"
    version = "llm_v1"

    async def analyze(self, context: ReportContext) -> ReportDraft:
        selected = select_representative(context.utterances)
        payload = await self._request(context, selected)
        allowed_quotes = {u.text.strip() for u in context.utterances if u.text.strip()}

        return ReportDraft(
            speech_summary=payload.speech_summary,
            vocabulary_feedback=payload.vocabulary_feedback,
            expression_patterns=payload.expression_patterns[:_MAX_PATTERNS],
            expression_items=self._to_items(payload.expression_items, allowed_quotes),
            logic_items=self._to_items(payload.logic_items, allowed_quotes),
            vocabularies=[
                DraftVocabulary(
                    word=word.word,
                    kind=word.kind,
                    definition=word.definition,
                    example_sentence=word.example_sentence,
                )
                for word in payload.vocabularies[:_MAX_WORDS]
            ],
            analyzer_name=f"{self.name}:{settings.ANTHROPIC_MODEL}",
            report_version=self.version,
            representative=(
                RepresentativeDraft(
                    message_id=selected.message_id,
                    text=selected.text.strip(),
                    elements=list(selected.elements),
                    reason=payload.representative_reason.strip() or describe_selection(selected),
                )
                if selected
                else None
            ),
            story_topic_questions=_to_prompts(payload.story_topic_questions),
            daily_life_questions=_to_prompts(payload.daily_life_questions),
        )

    async def _request(
        self, context: ReportContext, selected: UtteranceInput | None
    ) -> LLMReportPayload:
        response = await get_anthropic_client().messages.parse(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
            temperature=0.3,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(context, selected)}],
            output_format=LLMReportPayload,
        )
        if response.parsed_output is None:
            raise ValueError("LLM 응답을 리포트 형식으로 해석하지 못했습니다.")
        return response.parsed_output

    @staticmethod
    def _to_items(
        items: list[LLMExpressionItem] | list[LLMLogicItem],
        allowed_quotes: set[str],
    ) -> list[ReportFeedbackItem]:
        """LLM 이 만든 문장에 고정 라벨·설명을 붙이고, 지어낸 인용문은 걸러낸다."""
        result: list[ReportFeedbackItem] = []
        for item in items:
            label, description = _CRITERIA_BY_KEY[item.key]
            result.append(
                ReportFeedbackItem(
                    key=item.key,
                    label=label,
                    description=description,
                    quotes=[q for q in item.quotes if q.strip() in allowed_quotes][
                        :_MAX_QUOTES_PER_ITEM
                    ],
                    strength=item.strength,
                    tip=item.tip,
                )
            )
        return result


def _to_prompts(items: list[LLMConversationPrompt]) -> list[ConversationPrompt]:
    return [
        ConversationPrompt(question=item.question, practice_label=item.practice_label)
        for item in items[:_MAX_QUESTIONS_PER_GROUP]
    ]


def _build_user_prompt(context: ReportContext, selected: UtteranceInput | None) -> str:
    lines = [
        f"이야기 제목: {context.story_title}",
        f"아이 이름: {context.child_name}",
        "",
        "아이가 말한 문장 목록 (씬 번호 / 사고 요소 태그 / 발화):",
    ]
    if context.utterances:
        lines += [
            f"- 씬{u.scene_order} [{', '.join(u.elements) or '태그 없음'}] {u.text.strip()}"
            for u in context.utterances
            if u.text.strip()
        ]
    else:
        lines.append("- (발화 없음)")

    lines += ["", "분석 항목 정의:"]
    lines += [
        f"- {key} ({label}): {description}"
        for key, label, description in EXPRESSION_CRITERIA + LOGIC_CRITERIA
    ]

    lines += ["", "대표 발화:"]
    if selected:
        tags = ", ".join(selected.elements) or "태그 없음"
        lines.append(f"- [{tags}] {selected.text.strip()}")
        lines.append("이 발화를 왜 잘 말했다고 보는지 representative_reason 에 한 문장으로 적어라.")
    else:
        lines.append("- 없음. representative_reason 은 빈 문자열로 둔다.")

    return "\n".join(lines)


@lru_cache
def get_report_analyzer() -> ReportAnalyzer:
    """API 키가 없으면 스텁으로 동작한다 (로컬 개발·테스트용)."""
    if is_llm_configured():
        return LLMReportAnalyzer()
    return StubReportAnalyzer()
