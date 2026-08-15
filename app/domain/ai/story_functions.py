import json
from io import BytesIO
from typing import Any, BinaryIO

from app.core.ai_clients import get_groq_client, get_openai_client
from app.core.config import settings

ChatMessage = dict[str, str]


def _for_openai(chat_history: list[ChatMessage]) -> list[ChatMessage]:
    mapped: list[ChatMessage] = []
    for item in chat_history:
        role = item.get("role", "")
        if role == "AI":
            role = "assistant"
        elif role not in ("user", "assistant", "system"):
            role = "assistant"
        mapped.append({"role": role, "content": item.get("content", "")})
    return mapped


_REPORT_SYSTEM_PROMPT = (
    "너는 아이의 말하기 학습을 돕는 언어 교육 전문가야.\n"
    "아이와 동화 속 캐릭터가 나눈 대화 기록(chat_history)을 분석해서, "
    "아래 JSON 형식에 맞춰 보고서를 작성해줘.\n"
    "다른 설명, 코드블록(```) 없이 순수 JSON만 출력해.\n\n"
    "각 항목 작성 기준:\n"
    "1. speech_characteristics.comment: 아이(user)의 발화들을 분석해서 말하기 특징과 "
    "한줄 조언을 합쳐 2문장으로 작성.\n"
    "2. vocabulary.key_words: 아이가 실제로 사용한 주요 어휘 5~6개를 배열로.\n"
    "3. vocabulary.frequent_expressions: 아이가 자주 사용한 표현 패턴을 배열로.\n"
    "4. expression.perspective_empathy / emotion / interaction: 각각 관점과 공감, "
    "감정 표현, 상호작용 측면에서 comment(한줄 평), best_sentence(가장 잘 표현한 문장, "
    "아이가 실제로 말한 문장 중에서 선택), feedback(그 문장에 대한 평가와 조언)을 작성.\n"
    "5. logic.thought_reason / result_solution: 각각 생각과 이유, 결과와 해결 측면에서 "
    "comment, best_sentence(아이가 실제로 말한 문장 중에서 선택), feedback을 작성.\n"
    "6. feedback 항목은 반드시 두 부분으로 구성: 앞부분은 문장에 대한 '평가', "
    "뒷부분은 '조언'. 평가와 조언 사이에는 반드시 줄바꿈 문자 \\n 을 넣어서 "
    "하나의 문자열로 작성해. (예: \"평가 문장.\\n조언 문장.\")\n"
    "7. today_key_utterance: 아이의 발화 중 대표 문장 하나를 sentence로, "
    "선정 이유를 reason으로 작성.\n"
    "8. home_extension.story_topics: 이야기 속 상황을 아이가 더 생각해볼 수 있는 "
    "질문 3개와 각 질문이 어떤 연습인지를 purpose로 작성.\n"
    "9. home_extension.daily_life_questions: 이야기 내용을 아이의 일상생활과 연결짓는 "
    "질문 3개와 각 질문이 어떤 연습인지를 purpose로 작성.\n"
    "10. purpose 필드는 문장이 아니라 '관점추론연습', '감정표현연습', '인과추론연습', "
    "'자기성찰연습'처럼 명사형으로 무슨 연습인지만 짧게 작성해.\n\n"
    "best_sentence 항목들은 반드시 chat_history 안 아이(user)의 실제 발화에서 골라야 해. "
    "지어내지마.\n\n"
    "JSON 형식:\n"
    "{\n"
    '  "speech_characteristics": {"comment": ""},\n'
    '  "vocabulary": {"key_words": [], "frequent_expressions": []},\n'
    '  "expression": {\n'
    '    "perspective_empathy": {"comment": "", "best_sentence": "", "feedback": ""},\n'
    '    "emotion": {"comment": "", "best_sentence": "", "feedback": ""},\n'
    '    "interaction": {"comment": "", "best_sentence": "", "feedback": ""}\n'
    "  },\n"
    '  "logic": {\n'
    '    "thought_reason": {"comment": "", "best_sentence": "", "feedback": ""},\n'
    '    "result_solution": {"comment": "", "best_sentence": "", "feedback": ""}\n'
    "  },\n"
    '  "today_key_utterance": {"sentence": "", "reason": ""},\n'
    '  "home_extension": {\n'
    '    "story_topics": [\n'
    '      {"question": "", "purpose": ""},\n'
    '      {"question": "", "purpose": ""},\n'
    '      {"question": "", "purpose": ""}\n'
    "    ],\n"
    '    "daily_life_questions": [\n'
    '      {"question": "", "purpose": ""},\n'
    '      {"question": "", "purpose": ""},\n'
    '      {"question": "", "purpose": ""}\n'
    "    ]\n"
    "  }\n"
    "}"
)


def _read_audio(m4a_file: BinaryIO | BytesIO | bytes) -> tuple[str, bytes]:
    if isinstance(m4a_file, (bytes, bytearray)):
        return "audio.m4a", bytes(m4a_file)
    if hasattr(m4a_file, "seek"):
        m4a_file.seek(0)
    data = m4a_file.read()
    name = getattr(m4a_file, "name", "audio.m4a")
    filename = str(name).rsplit("/", 1)[-1] or "audio.m4a"
    return filename, data


def do_stt(m4a_file: BinaryIO | BytesIO | bytes, main_description: str) -> str:
    filename, data = _read_audio(m4a_file)
    if not data:
        return ""

    transcription = get_groq_client().audio.transcriptions.create(
        file=(filename, data),
        model=settings.GROQ_STT_MODEL,
        temperature=0,
        response_format="verbose_json",
    )
    raw_text = transcription.text.strip()
    if not raw_text:
        return ""

    normalize_system_prompt = (
        "너는 전문 STT(Speech-to-Text) 추출 텍스트 정규화 전문가야. 너의 임무는 입력되는 STT 텍스트를 "
        "원문의 형태와 의미를 완전히 보존하면서, 지정된 이야기 문맥에 맞게 자연스러운 문장으로 정규화(정리)하는 것이다.\n"
        "아래는 이 대화의 배경이 되는 동화 내용이야:\n"
        f"{main_description}\n\n"
        "규칙:\n"
        "- 원문의 구조 보존: 원문의 어순, 문장 구조, 띄어쓰기, 쉼표, 표현 방식을 임의로 수정하거나 생략하지 마라.\n"
        "- 이야기 문맥 반영: 음성 인식 오류(오타, 동음이의어 등)가 있을 경우, 위에서 제공된 "
        "'이야기 주제'와 문맥에 가장 알맞은 단어로 교정하라. "
        "(예: 삼국지 이야기인데 '관우'가 '과 누'로 인식되었다면 '관우'로 교정)\n"
        "- 주관적 추가 금지: AI 자의적으로 새로운 내용을 덧붙이거나, 원문에 없는 살을 붙이지 마라. "
        "문맥에 맞는 오타 교정과 띄어쓰기, 맞춤법 정리에만 집중하라."
        "- 출력 형식: 다른 설명(예: '정정된 문장입니다' 등)은 일절 제외하고, "
        "오직 정규화가 완료된 결과 텍스트만 출력하라."
    )

    completion = get_openai_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": normalize_system_prompt},
            {"role": "user", "content": raw_text},
        ],
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    return (completion.choices[0].message.content or "").strip()


def make_chat(
    character_name: str,  # 한글 표시명만. ch_banggui_... 같은 슬러그 금지.
    character_opening: str,
    character_closing: str,
    chat_history: list[ChatMessage],
    main_description: str,
    scene_description: str,
    scene_goal: str,
    turn: int,
) -> str:
    if turn == 0:
        return character_opening

    system_prompt = (
        f"너는 동화 속 캐릭터 '{character_name}'로서 아이와 대화하는 역할이야.\n\n"
        f"[전체 이야기]\n{main_description}\n\n"
        f"[현재 장면]\n{scene_description}\n\n"
        f"[이 대화의 목적]\n{scene_goal}\n\n"
        f"[이 장면의 시작 대사]\n{character_opening}\n\n"
        f"[이 장면의 마지막 대사 (아직 도달하지 않음, 참고용)]\n{character_closing}\n\n"
        "지금은 장면의 시작과 끝 사이, 대화가 진행 중인 상태야. "
        f"{character_opening}과{character_closing}사이에 있을만한 대화를 만들어야해"
        f"{character_opening}과{character_closing}의 분위기를 보고 따라야한다"
        "아직 장면이 끝난 게 아니니 마지막 대사를 사용하거나 장면을 마무리 짓지 마.\n\n"
        "대사를 만들기 전에 반드시 아래 순서로 단계별로 생각해:\n"
        f"1. 나는 지금 '{character_name}'이고, 어떤 성격과 말투를 가지고 있는지.\n"
        "2. 지금까지 대화 흐름과 시작 대사를 참고했을 때, 지금 상황이 무엇이고 "
        "아이가 방금 한 말이 어떤 의미를 가지는지.\n"
        "3. 대화의 목적(scene_goal)을 향해 조금 더 다가가려면 캐릭터가 "
        "지금 무슨 말을 해야 할지 계획해.\n\n"
        "4. 이 대화 흐름이 마지막 대사와 자연스럽게 연결되는지 생각해"
        "규칙:\n"
        "- 아이 수준에 맞는 쉬운 표현을 사용해.\n"
        "- 전반적으로 마지막 대사와 어울리는 대사를 한다"
        "- 대화의 목적(scene_goal)을 자연스럽게 이끌어가되, 장면을 마무리 짓지 마.\n"
        "- 위 생각 과정을 거친 뒤, 최종적으로는 캐릭터의 대사 한 문장(또는 짧은 대화)만 출력해.\n"
        "- 생각 과정이나 설명은 절대 출력하지 말고, 캐릭터의 대사만 출력해."
    )

    scene_history = chat_history[-(turn * 2) :] if turn > 0 else []
    messages = [{"role": "system", "content": system_prompt}] + _for_openai(scene_history)

    completion = get_openai_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_completion_tokens=2048,
        top_p=1,
        stream=False,
        stop=None,
    )
    return (completion.choices[0].message.content or "").strip()


def make_report(chat_history: list[ChatMessage]) -> dict[str, Any]:
    messages = (
        [{"role": "system", "content": _REPORT_SYSTEM_PROMPT}]
        + _for_openai(chat_history)
        + [{"role": "user", "content": "위 대화를 분석해서 지정된 JSON 형식으로 보고서를 작성해줘."}]
    )

    completion = get_openai_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_completion_tokens=2048,
        top_p=1,
        response_format={"type": "json_object"},
        stream=False,
        stop=None,
    )

    raw_output = (completion.choices[0].message.content or "").strip()
    raw_output = raw_output.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {"raw": raw_output}


# gpt-5.6-luna structured outputs. 응답을 {"result": bool} 로 강제한다.
_RESULT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "judgement",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"result": {"type": "boolean"}},
            "required": ["result"],
            "additionalProperties": False,
        },
    },
}


def _slice_current_scene(chat_history: list[ChatMessage], turn: int) -> list[ChatMessage]:
    """이번 장면만 뒤에서 (turn+1)*2개(AI+아이 쌍)만큼 자른다."""
    needed = (turn + 1) * 2
    return chat_history[-needed:] if needed <= len(chat_history) else chat_history[:]


def _format_chat_history(scene_messages: list[ChatMessage]) -> str:
    lines = []
    for message in scene_messages:
        speaker = "캐릭터" if message.get("role") == "AI" else "아이"
        lines.append(f'{speaker}: {message.get("content", "")}')
    return "\n".join(lines) if lines else "(대화 없음)"


def _openai_judge(system: str, user: str, *, default: bool) -> bool:
    completion = get_openai_client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_completion_tokens=2048,
        reasoning_effort="low",
        response_format=_RESULT_SCHEMA,
    )
    try:
        result = json.loads(completion.choices[0].message.content or "")
        return bool(result.get("result", default))
    except Exception:
        return default


def check_end_condition(scene_goal: str, chat_history: list[ChatMessage], turn: int) -> bool:
    if not scene_goal.strip():
        return False
    history_text = _format_chat_history(_slice_current_scene(chat_history, turn))
    return _openai_judge(
        (
            "너는 동화 캐릭터와 대화하며 말하기 연습을 하는 아이를 위한 대화 진행 심판이다. "
            "장면 목표와 이번 장면의 대화 기록을 보고 이 장면의 대화를 지금 끝내야 하는지 판단해라. "
            "목표가 충분히 달성됐으면 종료(true), 아니면 계속(false). "
            '다른 말 없이 JSON만 출력: {"result": true 또는 false}'
        ),
        f"[장면 목표]\n{scene_goal}\n\n[이번 장면 대화 기록]\n{history_text}",
        default=False,
    )


def check_correct_chat(
    main_description: str,
    scene_description: str,
    chat_history: list[ChatMessage],
    turn: int,
    text: str,
) -> bool:
    history_text = _format_chat_history(_slice_current_scene(chat_history, turn))
    return _openai_judge(
        (
            "너는 동화 속 상황에 맞게 아이가 말했는지 확인하는 심판이다. "
            "이야기 설명, 현재 장면 설명, 이번 장면의 대화 기록을 참고해서 "
            "아이의 마지막 답변이 지금 상황과 흐름에 맞는지 판단해라. "
            "완벽한 문장이 아니어도 맥락에 맞으면 true, 완전히 무관하면 false. "
            '다른 말 없이 JSON만 출력: {"result": true 또는 false}'
        ),
        (
            f"[이야기 설명]\n{main_description}\n\n"
            f"[현재 장면 설명]\n{scene_description}\n\n"
            f"[이번 장면 대화 기록]\n{history_text}\n\n"
            f"[아이의 이번 답변]\n{text}"
        ),
        default=True,
    )


def check_mission_condition(chat_history: list[ChatMessage], mission_condition: str) -> bool:
    if not mission_condition.strip():
        return False
    history_text = _format_chat_history(chat_history[-2:])
    return _openai_judge(
        (
            "너는 동화 대화 서비스에서 미션 등장 시점을 판단하는 심판이다. "
            "가장 최근 대화 한 쌍이 주어진 미션 등장 조건을 충족했는지 판단해라. "
            "충족했다면 true, 아니면 false. "
            '다른 말 없이 JSON만 출력: {"result": true 또는 false}'
        ),
        f"[미션 등장 조건]\n{mission_condition}\n\n[최근 대화]\n{history_text}",
        default=False,
    )
