from io import BufferedReader, BytesIO
from typing import BinaryIO, Protocol, TypedDict

from app.core.ai_clients import is_story_ai_configured
from app.domain.ai.story_functions import check_correct_chat as run_check_correct_chat
from app.domain.ai.story_functions import check_end_condition as run_check_end_condition
from app.domain.ai.story_functions import check_mission_condition as run_check_mission_condition
from app.domain.ai.story_functions import do_stt as run_stt
from app.domain.ai.story_functions import make_chat as run_make_chat

BinaryAudio = BinaryIO | BytesIO | BufferedReader | bytes


class ChatMessage(TypedDict):
    role: str
    content: str


ChatHistory = list[ChatMessage]


def to_openai_messages(history: list[dict]) -> list[dict[str, str]]:
    """저장용 role=AI 를 OpenAI 가 받는 assistant 로 바꾼다."""
    messages: list[dict[str, str]] = []
    for item in history:
        content = (item.get("content") or item.get("text") or "").strip()
        if not content:
            continue
        stored_role = item.get("role") or item.get("speaker")
        role = "user" if stored_role in ("user", "child") else "assistant"
        messages.append({"role": role, "content": content})
    return messages


class StoryAI(Protocol):
    def do_stt(self, m4a_file: BinaryAudio, main_description: str) -> str: ...

    def check_correct_chat(
        self,
        main_description: str,
        scene_description: str,
        chat_history: ChatHistory,
        turn: int,
        text: str,
    ) -> bool: ...

    def check_mission_condition(
        self,
        chat_history: ChatHistory,
        mission_condition: str,
    ) -> bool: ...

    def check_end_condition(
        self,
        scene_goal: str,
        chat_history: ChatHistory,
        turn: int,
    ) -> bool: ...

    def make_chat(
        self,
        character_name: str,
        character_opening: str,
        character_closing: str,
        chat_history: list[dict[str, str]],
        main_description: str,
        scene_description: str,
        scene_goal: str,
        turn: int,
    ) -> str: ...


class OpenAIStoryAI:
    def do_stt(self, m4a_file: BinaryAudio, main_description: str) -> str:
        return run_stt(m4a_file, main_description)

    def check_correct_chat(
        self,
        main_description: str,
        scene_description: str,
        chat_history: ChatHistory,
        turn: int,
        text: str,
    ) -> bool:
        return run_check_correct_chat(
            main_description, scene_description, chat_history, turn, text
        )

    def check_mission_condition(
        self,
        chat_history: ChatHistory,
        mission_condition: str,
    ) -> bool:
        return run_check_mission_condition(chat_history, mission_condition)

    def check_end_condition(
        self,
        scene_goal: str,
        chat_history: ChatHistory,
        turn: int,
    ) -> bool:
        return run_check_end_condition(scene_goal, chat_history, turn)

    def make_chat(
        self,
        character_name: str,
        character_opening: str,
        character_closing: str,
        chat_history: list[dict[str, str]],
        main_description: str,
        scene_description: str,
        scene_goal: str,
        turn: int,
    ) -> str:
        return run_make_chat(
            character_name,
            character_opening,
            character_closing,
            chat_history,
            main_description,
            scene_description,
            scene_goal,
            turn,
        )


class UnimplementedStoryAI:
    def do_stt(self, m4a_file: BinaryAudio, main_description: str) -> str:
        raise RuntimeError("GROQ_API_KEY 와 OPENAI_API_KEY 가 필요합니다.")

    def check_correct_chat(
        self,
        main_description: str,
        scene_description: str,
        chat_history: ChatHistory,
        turn: int,
        text: str,
    ) -> bool:
        return bool(text.strip())

    def check_mission_condition(
        self,
        chat_history: ChatHistory,
        mission_condition: str,
    ) -> bool:
        return False

    def check_end_condition(
        self,
        scene_goal: str,
        chat_history: ChatHistory,
        turn: int,
    ) -> bool:
        return False

    def make_chat(
        self,
        character_name: str,
        character_opening: str,
        character_closing: str,
        chat_history: list[dict[str, str]],
        main_description: str,
        scene_description: str,
        scene_goal: str,
        turn: int,
    ) -> str:
        raise RuntimeError("OPENAI_API_KEY 가 필요합니다.")


def get_story_ai() -> StoryAI:
    if is_story_ai_configured():
        return OpenAIStoryAI()
    return UnimplementedStoryAI()
