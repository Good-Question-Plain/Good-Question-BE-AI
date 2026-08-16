from app.domain.vocabulary.analyzer import (
    EXPRESSION_CRITERIA,
    LOGIC_CRITERIA,
    DraftVocabulary,
    ReportContext,
    ReportDraft,
    RepresentativeDraft,
    UtteranceInput,
    describe_selection,
    select_representative,
)

_MAX_WORDS = 10
_MAX_PATTERNS = 3
_MAX_QUESTIONS_PER_GROUP = 3
from app.domain.vocabulary.schema import ConversationPrompt, ReportFeedbackItem

_EXPRESSION_KEYS = {
    "perspective_empathy": "perspective_empathy",
    "emotion": "emotion_expression",
    "interaction": "interaction",
}
_LOGIC_KEYS = {
    "thought_reason": "thought_reason",
    "result_solution": "outcome_solution",
}
_CRITERIA = {
    key: (label, description)
    for key, label, description in EXPRESSION_CRITERIA + LOGIC_CRITERIA
}


def _split_feedback(feedback: str) -> tuple[str, str]:
    parts = [part.strip() for part in (feedback or "").split("\n", 1)]
    strength = parts[0]
    tip = parts[1] if len(parts) > 1 else ""
    return strength, tip


def _allowed_quotes(utterances: list[UtteranceInput]) -> list[str]:
    return [u.text.strip() for u in utterances if u.text.strip()]


def _match_quote(text: str, allowed: list[str]) -> list[str]:
    candidate = (text or "").strip()
    if not candidate:
        return []
    if candidate in allowed:
        return [candidate]
    contained = [quote for quote in allowed if quote in candidate or candidate in quote]
    return contained[:1]


def _to_items(
    payload: dict,
    key_map: dict[str, str],
    allowed: list[str],
) -> list[ReportFeedbackItem]:
    items: list[ReportFeedbackItem] = []
    for raw_key, report_key in key_map.items():
        block = payload.get(raw_key) or {}
        label, description = _CRITERIA[report_key]
        strength, tip = _split_feedback(block.get("feedback") or "")
        if not strength:
            strength = (block.get("comment") or "").strip() or None
        items.append(
            ReportFeedbackItem(
                key=report_key,
                label=label,
                description=description,
                quotes=_match_quote(block.get("best_sentence") or "", allowed),
                strength=strength,
                tip=tip or None,
            )
        )
    return items


def _to_prompts(rows: list | None) -> list[ConversationPrompt]:
    prompts: list[ConversationPrompt] = []
    for row in rows or []:
        question = (row.get("question") or "").strip()
        purpose = (row.get("purpose") or "").strip()
        if question:
            prompts.append(ConversationPrompt(question=question, practice_label=purpose))
        if len(prompts) >= _MAX_QUESTIONS_PER_GROUP:
            break
    return prompts


def _representative(payload: dict, context: ReportContext) -> RepresentativeDraft | None:
    block = payload.get("today_key_utterance") or {}
    sentence = (block.get("sentence") or "").strip()
    reason = (block.get("reason") or "").strip()
    allowed = _allowed_quotes(context.utterances)

    matched = next((u for u in context.utterances if u.text.strip() == sentence), None)
    if matched is None and sentence:
        matched = next(
            (
                u
                for u in context.utterances
                if u.text.strip() and (u.text.strip() in sentence or sentence in u.text.strip())
            ),
            None,
        )
    if matched is None:
        matched = select_representative(context.utterances)
    if matched is None:
        if sentence and sentence in allowed:
            return RepresentativeDraft(
                message_id=context.utterances[0].message_id,
                text=sentence,
                elements=[],
                reason=reason,
            )
        return None

    return RepresentativeDraft(
        message_id=matched.message_id,
        text=matched.text.strip(),
        elements=list(matched.elements),
        reason=reason or describe_selection(matched),
    )


def map_make_report(payload: dict, context: ReportContext) -> ReportDraft:
    if payload.get("raw") and set(payload) == {"raw"}:
        raise ValueError("리포트 JSON을 해석하지 못했습니다.")

    vocabulary = payload.get("vocabulary") or {}
    expression = payload.get("expression") or {}
    logic = payload.get("logic") or {}
    home = payload.get("home_extension") or {}
    allowed = _allowed_quotes(context.utterances)
    key_words = [word.strip() for word in vocabulary.get("key_words") or [] if str(word).strip()]
    comment = ((payload.get("speech_characteristics") or {}).get("comment") or "").strip()

    return ReportDraft(
        speech_summary=comment,
        vocabulary_feedback=(
            f"아이가 「{', '.join(key_words[:6])}」 같은 어휘를 사용했어요."
            if key_words
            else "아이가 사용한 주요 어휘를 정리했어요."
        ),
        expression_patterns=[
            pattern.strip()
            for pattern in (vocabulary.get("frequent_expressions") or [])
            if str(pattern).strip()
        ][:_MAX_PATTERNS],
        expression_items=_to_items(expression, _EXPRESSION_KEYS, allowed),
        logic_items=_to_items(logic, _LOGIC_KEYS, allowed),
        vocabularies=[
            DraftVocabulary(word=word, kind="used") for word in key_words[:_MAX_WORDS]
        ],
        analyzer_name="openai:make_report",
        report_version="story_fn_v1",
        representative=_representative(payload, context),
        story_topic_questions=_to_prompts(home.get("story_topics")),
        daily_life_questions=_to_prompts(home.get("daily_life_questions")),
    )
