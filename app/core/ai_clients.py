from functools import lru_cache

from groq import Groq
from openai import OpenAI

from app.core.config import settings


def is_openai_configured() -> bool:
    return bool(settings.OPENAI_API_KEY)


def is_groq_configured() -> bool:
    return bool(settings.GROQ_API_KEY)


def is_story_ai_configured() -> bool:
    return is_openai_configured() and is_groq_configured()


@lru_cache
def get_openai_client() -> OpenAI:
    if not is_openai_configured():
        raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다.")
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
    )


@lru_cache
def get_groq_client() -> Groq:
    if not is_groq_configured():
        raise RuntimeError("GROQ_API_KEY 가 설정되지 않았습니다.")
    return Groq(api_key=settings.GROQ_API_KEY)
