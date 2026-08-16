from functools import lru_cache

from anthropic import AsyncAnthropic

from app.core.config import settings


def is_llm_configured() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    if not is_llm_configured():
        raise RuntimeError("ANTHROPIC_API_KEY 가 설정되지 않았습니다.")
    return AsyncAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.ANTHROPIC_TIMEOUT_SECONDS,
    )
