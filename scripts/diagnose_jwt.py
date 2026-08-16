"""
Supabase JWT 토큰 진단 스크립트
사용법: uv run python scripts/diagnose_jwt.py <access_token>
"""
import sys

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError


def diagnose(token: str) -> None:
    # Step 1: 검증 없이 claims 확인
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.get_unverified_claims(token)
        print("=== 토큰 헤더 ===")
        print(header)
        print("\n=== 토큰 Claims (검증 없음) ===")
        for k, v in claims.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"토큰 파싱 실패 (잘못된 형식): {e}")
        return

    # Step 2: 서버 설정으로 검증 시도
    try:
        from app.core.config import settings

        secret = settings.SUPABASE_JWT_SECRET
        print(f"\n=== 검증 시도 ===")
        print(f"  Secret 길이: {len(secret)}")
        print(f"  Secret 앞 8자: {secret[:8]}...")

        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        print("\n[SUCCESS] 토큰 검증 성공!")
        print(payload)

    except ExpiredSignatureError as e:
        print(f"\n[FAIL] 토큰 만료: {e}")
    except JWTClaimsError as e:
        print(f"\n[FAIL] Claim 불일치 (audience 등): {e}")
        print(f"  토큰의 aud: {claims.get('aud')!r}  (서버 기대값: 'authenticated')")
    except JWTError as e:
        print(f"\n[FAIL] 서명 검증 실패: {e}")
        print("  → SUPABASE_JWT_SECRET 값이 Supabase 대시보드의 JWT Secret과 다를 가능성이 높습니다.")
        print("  → Supabase Dashboard > Settings > API > JWT Settings > JWT Secret 확인")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: uv run python scripts/diagnose_jwt.py <access_token>")
        sys.exit(1)
    diagnose(sys.argv[1])
