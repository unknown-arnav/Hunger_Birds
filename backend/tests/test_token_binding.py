"""Access tokens are bound to a session, and carry the claims we require.

Signing out used to be half a feature. Revoking a session killed refreshing
immediately, but the access token already in someone's hands kept working until
it expired on its own - so "sign out everywhere", the button you press after
losing a phone, left whoever had the phone with up to ACCESS_TOKEN_EXPIRE_MINUTES
of continued access. The `sid` claim is what closes that, and these tests pin
both halves: that the claim is there, and that a token without one is refused.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    REQUIRED_CLAIMS,
    TokenType,
    create_access_token,
    decode_token,
)


def _sign(payload: dict) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _valid_payload(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "type": TokenType.ACCESS.value,
        "iat": now,
        "exp": now + timedelta(minutes=10),
        "sid": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


# --- The sid claim ----------------------------------------------------------


def test_an_access_token_names_the_session_that_issued_it():
    user_id, session_id = str(uuid.uuid4()), str(uuid.uuid4())
    claims = decode_token(create_access_token(user_id, session_id))
    assert claims["sub"] == user_id
    assert claims["sid"] == session_id
    assert claims["type"] == TokenType.ACCESS.value


def test_two_sessions_for_one_user_get_distinguishable_tokens():
    """Ending one device must not end the others, which needs the tokens to say
    which device they belong to."""
    user_id = str(uuid.uuid4())
    phone = decode_token(create_access_token(user_id, str(uuid.uuid4())))
    laptop = decode_token(create_access_token(user_id, str(uuid.uuid4())))
    assert phone["sub"] == laptop["sub"]
    assert phone["sid"] != laptop["sid"]


# --- Required claims --------------------------------------------------------


def test_exp_is_required_not_merely_checked_when_present():
    """A validly-signed token with no exp was accepted forever.

    PyJWT only validates an expiry it can find, so omitting the claim skipped the
    check rather than failing it. Verified against the running app: such a token
    returned 200 on /auth/me. It takes the signing secret to forge one, so this
    is the difference between a leaked secret being bad and being permanent.
    """
    token = _sign({"sub": str(uuid.uuid4()), "type": "access", "sid": str(uuid.uuid4())})
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_token(token)


@pytest.mark.parametrize("missing", REQUIRED_CLAIMS)
def test_every_required_claim_is_enforced(missing):
    payload = _valid_payload()
    del payload[missing]
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_token(_sign(payload))


def test_an_expired_token_is_still_refused():
    now = datetime.now(timezone.utc)
    token = _sign(_valid_payload(iat=now - timedelta(hours=2), exp=now - timedelta(hours=1)))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_a_token_signed_with_another_secret_is_refused():
    payload = _valid_payload()
    forged = jwt.encode(payload, "b" * 64, algorithm="HS256")  # wrong, but long enough not to warn
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(forged)


def test_an_unsigned_token_is_refused():
    """alg=none is the oldest JWT trick and must not survive the claim changes."""
    payload = _valid_payload()
    unsigned = jwt.encode(payload, key="", algorithm="none")
    with pytest.raises(jwt.PyJWTError):
        decode_token(unsigned)


# --- Every route that issues a token must bind it to a session ---------------


def test_create_access_token_cannot_be_called_without_a_session():
    """The guard that makes forgetting impossible rather than merely unlikely.

    Three routes issue access tokens - OTP verify, refresh, and the admin
    password login - and a fourth could be added tomorrow. Making session_id a
    required positional argument means a route that forgets it fails loudly at
    the call rather than quietly minting a token that nothing can revoke, which
    is exactly what every one of these tokens used to be.

    This is worth pinning: giving session_id a default would silently restore the
    old behaviour for any caller that omitted it.
    """
    import inspect

    signature = inspect.signature(create_access_token)
    session_param = signature.parameters["session_id"]
    assert session_param.default is inspect.Parameter.empty, (
        "session_id must stay required; a default would let a route mint an "
        "unrevocable token by omitting it"
    )

    with pytest.raises(TypeError):
        create_access_token(str(uuid.uuid4()))  # type: ignore[call-arg]


def test_every_token_issuing_route_passes_a_session():
    """Read the auth router and check each create_access_token call site.

    The runtime signature above catches an omission the moment the route is
    exercised, but a login path that only runs when ADMIN_PASSWORD_HASH is set
    can sit untested for a long time - which is precisely the case that broke
    when the admin password door met this change.
    """
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "app" / "modules" / "auth" / "router.py"
    tree = ast.parse(source.read_text())

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "create_access_token"
    ]
    assert len(calls) >= 3, f"expected the three token-issuing routes, found {len(calls)}"
    for call in calls:
        assert len(call.args) == 2, (
            f"create_access_token at line {call.lineno} does not pass a session id"
        )
