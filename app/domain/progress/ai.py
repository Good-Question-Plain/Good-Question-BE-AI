from io import BufferedReader, BytesIO
from typing import BinaryIO, Protocol, TypedDict

BinaryAudio = BinaryIO | BytesIO | BufferedReader


class ChatTurn(TypedDict):
    speaker: str
    text: str


class ChatHistory(TypedDict):
    turns: list[ChatTurn]


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
        chat_history: ChatHistory,
        main_description: str,
        scene_description: str,
        scene_goal: str,
        turn: int,
    ) -> str: ...


class UnimplementedStoryAI:
    def do_stt(self, m4a_file: BinaryAudio, main_description: str) -> str:
        # AI 이후 개발
        pass

    def check_correct_chat(
        self,
        main_description: str,
        scene_description: str,
        chat_history: ChatHistory,
        turn: int,
        text: str,
    ) -> bool:
        # AI 이후 개발
        pass

    def check_mission_condition(
        self,
        chat_history: ChatHistory,
        mission_condition: str,
    ) -> bool:
        # AI 이후 개발
        pass

    def check_end_condition(
        self,
        scene_goal: str,
        chat_history: ChatHistory,
        turn: int,
    ) -> bool:
        # AI 이후 개발
        pass

    def make_chat(
        self,
        chat_history: ChatHistory,
        main_description: str,
        scene_description: str,
        scene_goal: str,
        turn: int,
    ) -> str:
        # AI 이후 개발
        pass


def get_story_ai() -> StoryAI:
    return UnimplementedStoryAI()
