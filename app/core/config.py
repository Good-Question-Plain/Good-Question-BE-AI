from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str = ""  # 레거시 HS256 방식에서 사용, 현재는 JWKS로 대체됨
    SUPABASE_SERVICE_ROLE_KEY: str

    @property
    def supabase_base_url(self) -> str:
        """REST API 경로가 포함된 URL도 안전하게 base URL만 반환"""
        from urllib.parse import urlparse
        parsed = urlparse(self.SUPABASE_URL)
        return f"{parsed.scheme}://{parsed.netloc}"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "ap-northeast-2"

    # Anthropic (학습 리포트 분석, OpenAI 키가 없을 때 폴백)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_MAX_TOKENS: int = 2000
    ANTHROPIC_TIMEOUT_SECONDS: float = 60.0

    # OpenAI (STT 정규화, 장면 심판, 캐릭터 대사, 학습 리포트)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-luna"
    OPENAI_TIMEOUT_SECONDS: float = 60.0

    # Groq (Whisper STT)
    GROQ_API_KEY: str = ""
    GROQ_STT_MODEL: str = "whisper-large-v3"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Cloudflare
    CLOUDFLARE_TUNNEL_TOKEN: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
