"""Guards on deployment configuration that code review alone would miss."""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

START_COMMAND_FILES = [
    REPO / "railway.json",
    REPO / "backend" / "Dockerfile",
    REPO / "backend" / "Procfile",
]


@pytest.mark.parametrize("path", START_COMMAND_FILES, ids=lambda p: p.name)
def test_uvicorn_is_started_without_proxy_header_handling(path):
    """Every start command must pass --no-proxy-headers.

    Uvicorn's default rewrites request.client from the leftmost X-Forwarded-For
    entry, which is the one a caller can forge. The rate limiter reads that
    header itself, from the right, counting only hops it is told to trust - and
    that is defeated outright if uvicorn has already substituted a forged value
    underneath it. Dropping this flag silently makes every per-IP limit in
    app/core/limits.py bypassable, with nothing failing to show it, which is
    why it is asserted here rather than left to a comment.
    """
    text = path.read_text()
    assert "uvicorn" in text, f"{path.name} no longer starts uvicorn; update this test"
    for line in text.splitlines():
        if "uvicorn app.main:app" in line and "--reload" not in line:
            assert "--no-proxy-headers" in line, f"{path.name}: {line.strip()}"


def test_healthcheck_targets_the_readiness_probe():
    """/health/ready checks Postgres and Redis; /health only proves the process
    is up, so a deploy that cannot reach its databases would still go live."""
    config = json.loads((REPO / "railway.json").read_text())
    assert config["deploy"]["healthcheckPath"] == "/health/ready"


def test_migrations_run_before_a_release_takes_traffic():
    config = json.loads((REPO / "railway.json").read_text())
    assert "alembic upgrade head" in config["deploy"]["preDeployCommand"]


def test_the_example_env_does_not_ship_a_usable_secret():
    example = (REPO / "backend" / ".env.example").read_text()
    for line in example.splitlines():
        if line.startswith("JWT_SECRET="):
            value = line.split("=", 1)[1]
            assert "change-me" in value, "the example must not look like a real secret"
        # Credentials must never be committed, even as examples.
        if line.startswith(("RESEND_API_KEY=", "CLOUDINARY_API_SECRET=")):
            assert line.split("=", 1)[1].strip() == ""


# --- The signing secret -----------------------------------------------------
#
# A forged access token is indistinguishable from a real one, so JWT_SECRET is
# the single thing holding up every authorisation check in the app. Nothing used
# to check it: a deployment that shipped the placeholder from .env.example
# started cleanly, passed the healthcheck, and served traffic while anyone who
# had read this repository could mint a token for any account, admin included.


def _settings(**overrides):
    from app.core.config import Settings

    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "redis_url": "redis://localhost:6379/0",
        "jwt_secret": "a" * 64,
    }
    base.update(overrides)
    return Settings(**base)


def test_a_generated_secret_is_accepted():
    import secrets

    assert _settings(jwt_secret=secrets.token_hex(32)).production_config_errors() == []


def test_the_placeholder_from_the_example_env_is_refused():
    example = (REPO / "backend" / ".env.example").read_text()
    placeholder = next(
        line.split("=", 1)[1]
        for line in example.splitlines()
        if line.startswith("JWT_SECRET=")
    )
    errors = _settings(jwt_secret=placeholder).production_config_errors()
    assert errors, "the documented placeholder must not pass as a production secret"


def test_a_short_secret_is_refused():
    errors = _settings(jwt_secret="abc123").production_config_errors()
    assert any("characters long" in e for e in errors)


@pytest.mark.parametrize(
    "secret",
    [
        "change-me-to-a-long-random-string-but-longer-now",
        "your-secret-key-goes-right-here-and-is-long-enough",
        "PLACEHOLDER-value-that-is-definitely-long-enough-xx",
        "supersecret-but-still-long-enough-to-pass-the-length",
    ],
)
def test_long_but_obviously_copied_secrets_are_refused(secret):
    """Length alone is not evidence of randomness."""
    assert _settings(jwt_secret=secret).production_config_errors()


def test_development_is_left_alone():
    """Local work must not need a generated secret to boot."""
    config = _settings(jwt_secret="change-me", environment="development")
    assert config.production_config_errors() == []


def test_anything_that_is_not_development_is_treated_as_production():
    for environment in ("production", "staging", "", "PROD"):
        config = _settings(jwt_secret="change-me", environment=environment)
        assert config.production_config_errors(), f"{environment!r} was not gated"
