from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings


async def send_otp_email(to_email: str, otp: str) -> None:
    message = MIMEText(
        f"인증 코드: {otp}\n\n유효 시간: {settings.OTP_EXPIRE_MINUTES}분\n\n"
        "이 메일은 Good Question 서비스에서 발송되었습니다.",
        _charset="utf-8",
    )
    message["From"] = settings.SMTP_USER
    message["To"] = to_email
    message["Subject"] = "[Good Question] 이메일 인증 코드"

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )
