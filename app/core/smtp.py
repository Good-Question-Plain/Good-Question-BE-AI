from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings


async def _send(to_email: str, subject: str, body: str) -> None:
    message = MIMEText(body, _charset="utf-8")
    message["From"] = settings.SMTP_USER
    message["To"] = to_email
    message["Subject"] = subject
    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )


async def send_otp_email(to_email: str, otp: str) -> None:
    await _send(
        to_email,
        "[Good Question] 이메일 인증 코드",
        f"인증 코드: {otp}\n\n유효 시간: {settings.OTP_EXPIRE_MINUTES}분\n\n"
        "이 메일은 Good Question 서비스에서 발송되었습니다.",
    )


async def send_reset_password_email(to_email: str, otp: str) -> None:
    await _send(
        to_email,
        "[Good Question] 비밀번호 재설정 코드",
        f"비밀번호 재설정 코드: {otp}\n\n유효 시간: {settings.OTP_EXPIRE_MINUTES}분\n\n"
        "본인이 요청하지 않은 경우 이 메일을 무시하세요.\n\n"
        "이 메일은 Good Question 서비스에서 발송되었습니다.",
    )
