from datetime import datetime, timedelta, timezone
from enum import StrEnum

import jwt

from app.core.config import get_settings


class TokenType(StrEnum):
    """Access tokens are JWTs; refresh tokens are not.

    Refresh tokens moved to opaque, database-backed session keys so they can be
    revoked (see modules/auth/sessions.py). REFRESH stays here so that any JWT
    still carrying it - issued before that change, or forged - fails the
    "is this an access token" check in deps.get_current_user rather than being
    treated as one.
    """

    ACCESS = "access"
    REFRESH = "refresh"


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    *,
    session_id: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    if session_id is not None:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, session_id: str) -> str:
    """Mint an access token bound to the session that issued it.

    The `sid` claim is what makes signing out real. Without it an access token
    is a bearer credential that nothing can take back: revoking the session
    killed refreshing, but the access token already in someone's hands kept
    working until it expired on its own - up to ACCESS_TOKEN_EXPIRE_MINUTES
    after the user pressed "sign out everywhere". With it, get_current_user can
    check the session row on every request and a revocation lands immediately.
    """
    settings = get_settings()
    return _create_token(
        user_id,
        TokenType.ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
        session_id=session_id,
    )


# Claims every access token must carry. Spelled out because PyJWT only
# validates `exp` when it happens to be present: a token signed with our secret
# but carrying no `exp` was accepted forever, which turns a leaked secret from
# bad into unrecoverable.
REQUIRED_CLAIMS = ["exp", "iat", "sub", "type"]


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": REQUIRED_CLAIMS},
    )
