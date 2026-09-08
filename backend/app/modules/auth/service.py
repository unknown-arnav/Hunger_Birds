import secrets

import resend
from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import Settings

OTP_TTL_SECONDS = 5 * 60
OTP_RATE_LIMIT_SECONDS = 60


def normalize_email(email: str) -> str:
    """Lowercase and strip +tag local-part addressing so name+1@x and name@x
    resolve to the same account (closes an easy multi-account loophole)."""
    local, _, domain = email.strip().lower().partition("@")
    local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def assert_allowed_domain(email: str, settings: Settings) -> None:
    domain = email.rsplit("@", 1)[-1].lower()
    if domain != settings.allowed_email_domain.lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Only @{settings.allowed_email_domain} email addresses may sign up.",
        )


def _otp_key(email: str) -> str:
    return f"otp:code:{email}"


def _rate_limit_key(email: str) -> str:
    return f"otp:rl:{email}"


async def request_otp(email: str, redis: Redis, settings: Settings) -> str | None:
    """Generates and stores an OTP, sends it via Resend. Returns the code
    only when OTP_DEBUG_ECHO is enabled, for local-dev convenience."""
    if await redis.get(_rate_limit_key(email)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Please wait a minute before requesting another code.",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    await redis.set(_otp_key(email), code, ex=OTP_TTL_SECONDS)
    await redis.set(_rate_limit_key(email), "1", ex=OTP_RATE_LIMIT_SECONDS)

    if settings.resend_api_key:
        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [email],
                "subject": "Your Hunger Birds login code",
                "html": (
                    f"<p>Your Hunger Birds login code is:</p>"
                    f"<h2>{code}</h2>"
                    f"<p>It expires in 5 minutes. If you didn't request this, ignore this email.</p>"
                ),
            }
        )

    return code if settings.otp_debug_echo else None


async def verify_otp(email: str, code: str, redis: Redis) -> bool:
    stored = await redis.get(_otp_key(email))
    if stored is None or stored != code:
        return False
    await redis.delete(_otp_key(email))
    return True
