"""
E2E 검증 스크립트 — JWT 수정 및 sync-profile 흐름 검증
실행: uv run python scripts/e2e_verify.py
"""
import asyncio
import httpx
from app.core.config import settings

API_BASE = "http://localhost:8001"
SUPABASE_AUTH = f"{settings.SUPABASE_URL}/auth/v1"
ADMIN_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}
TEST_EMAIL = "e2e_verify_test@goodquestion.dev"
TEST_PASSWORD = "TestPassword123!"
TEST_NAME = "E2E테스트유저"


async def step(label: str, ok: bool, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    print(f"  [{mark}] {label}" + (f": {detail}" if detail else ""))
    if not ok:
        raise SystemExit(1)


async def main() -> None:
    print("\n=== Supabase JWT E2E 검증 ===\n")

    async with httpx.AsyncClient(timeout=15) as client:

        # 1. JWKS 엔드포인트 확인
        print("[1] JWKS 엔드포인트 확인")
        r = await client.get(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        await step("JWKS 응답", r.status_code == 200)
        keys = r.json().get("keys", [])
        ecc_keys = [k for k in keys if k.get("kty") == "EC"]
        await step("ECC 키 존재 여부", len(ecc_keys) > 0, f"{len(ecc_keys)}개 ECC 키")

        # 2. 서버 헬스 체크
        print("\n[2] 서버 헬스 체크")
        r = await client.get(f"{API_BASE}/docs")
        await step("서버 응답", r.status_code == 200)

        # 3. 테스트 유저 생성 (admin API)
        print("\n[3] 테스트 유저 생성")
        r = await client.post(
            f"{SUPABASE_AUTH}/admin/users",
            headers=ADMIN_HEADERS,
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "email_confirm": True},
        )
        created = r.status_code in (200, 201)
        if not created and r.status_code == 422:
            # 이미 존재하면 삭제 후 재생성
            search = await client.get(
                f"{SUPABASE_AUTH}/admin/users?email={TEST_EMAIL}", headers=ADMIN_HEADERS
            )
            users = search.json().get("users", [])
            if users:
                await client.delete(
                    f"{SUPABASE_AUTH}/admin/users/{users[0]['id']}", headers=ADMIN_HEADERS
                )
            r = await client.post(
                f"{SUPABASE_AUTH}/admin/users",
                headers=ADMIN_HEADERS,
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "email_confirm": True},
            )
            created = r.status_code in (200, 201)
        await step("테스트 유저 생성", created, f"status={r.status_code}")
        test_user_id = r.json().get("id") or r.json().get("user", {}).get("id")

        # 4. 로그인 → JWT 발급
        print("\n[4] Supabase 로그인 (JWT 발급)")
        r = await client.post(
            f"{SUPABASE_AUTH}/token?grant_type=password",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": "application/json",
            },
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        await step("로그인 성공", r.status_code == 200, f"status={r.status_code}")
        access_token = r.json().get("access_token")
        await step("access_token 수신", bool(access_token))
        AUTH_HEADER = {"Authorization": f"Bearer {access_token}"}

        # 5. JWT 검증 (서버 측)
        print("\n[5] JWT 검증 — sync-profile 호출 전 (parents 레코드 없음)")
        r = await client.get(f"{API_BASE}/users/me", headers=AUTH_HEADER)
        await step(
            "parents 레코드 없음 → 401 반환 확인",
            r.status_code == 401,
            f"status={r.status_code}",
        )

        # 6. sync-profile 호출 → parents 레코드 생성
        print("\n[6] POST /auth/sync-profile")
        r = await client.post(
            f"{API_BASE}/auth/sync-profile",
            headers=AUTH_HEADER,
            json={"name": TEST_NAME},
        )
        await step("sync-profile 성공", r.status_code == 201, f"status={r.status_code}, body={r.text}")

        # 7. /users/me 정상 조회 확인
        print("\n[7] GET /users/me — parents 레코드 생성 후")
        r = await client.get(f"{API_BASE}/users/me", headers=AUTH_HEADER)
        await step("/users/me 200 응답", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        await step("name 일치", data.get("name") == TEST_NAME, f"name={data.get('name')!r}")

        # 8. /users/me/children 확인
        print("\n[8] GET /users/me/children")
        r = await client.get(f"{API_BASE}/users/me/children", headers=AUTH_HEADER)
        await step("/users/me/children 200 응답", r.status_code == 200, f"status={r.status_code}")
        await step("빈 배열 반환", r.json() == [], f"body={r.text}")

        # 9. 테스트 유저 정리
        print("\n[9] 테스트 데이터 정리")
        if test_user_id:
            r = await client.delete(
                f"{SUPABASE_AUTH}/admin/users/{test_user_id}", headers=ADMIN_HEADERS
            )
            await step("테스트 유저 삭제", r.status_code in (200, 204), f"status={r.status_code}")

    print("\n=== 모든 검증 통과 ===\n")


asyncio.run(main())
