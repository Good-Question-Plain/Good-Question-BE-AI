from jose import jwt

from app.core.config import settings


def verify_supabase_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )
