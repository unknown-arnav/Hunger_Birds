from functools import lru_cache
from ipaddress import ip_address, ip_network

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# A forged access token is indistinguishable from a real one, so the signing
# secret is the single thing holding up every authorisation check in the app.
MIN_JWT_SECRET_LENGTH = 32

# Substrings that mark a secret as copied from documentation rather than
# generated. Kept to unambiguous placeholders: a real `openssl rand -hex 32`
# value contains none of them, and a broader list would reject good secrets.
_PLACEHOLDER_SECRET_MARKERS = (
    "change-me",
    "changeme",
    "replace-me",
    "placeholder",
    "example",
    "your-secret",
    "supersecret",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str

    resend_api_key: str = ""
    resend_from_email: str = "Hungry Birds <onboarding@resend.dev>"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # "development" unlocks local conveniences (permissive CORS, the OTP debug
    # echo). Anything else - including the default - is treated as production,
    # so a deployment is safe unless someone deliberately declares otherwise.
    environment: str = "production"

    allowed_email_domain: str = "bitmesra.ac.in"

    # Lets an admin sign in with a password instead of waiting on an OTP email,
    # which matters because the admin is the account you need when email itself
    # is the thing that is broken. Empty disables the endpoint entirely, so the
    # extra way in does not exist unless it is deliberately configured.
    # Generate with: python scripts/set_admin_password.py
    admin_password_hash: str = ""

    # Returns login codes in API responses. That is a complete authentication
    # bypass, so it is honoured only in development; see debug_echo_enabled.
    otp_debug_echo: bool = False

    # Which peers are allowed to speak for someone else via X-Forwarded-For,
    # as a comma-separated list of addresses or CIDR blocks.
    #
    # Empty (the default) means any peer is believed, which is correct on a
    # platform where the app is only reachable through the platform's own edge -
    # Railway, for instance, where nothing else can open a connection to the
    # container from outside the project. Set it when the app is reachable by
    # anything else, because with TRUSTED_PROXY_COUNT=1 a single forged header
    # entry is indistinguishable from one a real proxy added: reading from the
    # right cannot tell them apart, only knowing who connected can.
    trusted_proxy_hosts: str = ""

    # How many reverse proxies sit in front of this app. Railway is exactly one.
    # Used to find the real client address for rate limiting without trusting
    # the part of X-Forwarded-For that a caller can forge - see client_ip().
    # 0 means nothing is in front and the header is ignored entirely.
    trusted_proxy_count: int = 1

    # Bodies larger than this are refused before they are parsed, so a single
    # request cannot chew through memory.
    max_request_bytes: int = 256 * 1024

    # A blanket per-IP ceiling across the whole API, on top of the per-endpoint
    # limits. Generous enough that ordinary browsing never notices it.
    global_rate_limit_requests: int = 300
    global_rate_limit_seconds: int = 60

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_upload_folder: str = "hunger_birds"

    # Empty means send no CORS headers at all, which is correct in production:
    # the backend serves the web app itself, so every call is same-origin and
    # no other site has any business calling this API. Set it to a
    # comma-separated origin list only if a separate frontend host is added.
    cors_origins: str = ""

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, value: str) -> str:
        """Railway (and most hosts) inject a plain postgres:// URL, but the
        async engine needs the asyncpg driver spelled out."""
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
            if value.startswith(prefix):
                return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def is_development(self) -> bool:
        return self.environment.strip().lower() in {"development", "dev", "local"}

    @property
    def debug_echo_enabled(self) -> bool:
        """OTP codes echoed in responses - development only.

        Deliberately gated on two settings rather than one. OTP_DEBUG_ECHO is
        the kind of variable that gets copied into a production environment by
        accident, and on its own it would hand anyone a login as anyone,
        including the admin. Requiring ENVIRONMENT=development as well means
        that mistake is inert.
        """
        return self.otp_debug_echo and self.is_development

    @property
    def trusted_proxy_networks(self) -> tuple:
        """The configured peers, parsed. Unparseable entries are dropped."""
        networks = []
        for raw in self.trusted_proxy_hosts.split(","):
            candidate = raw.strip()
            if not candidate:
                continue
            try:
                networks.append(ip_network(candidate, strict=False))
            except ValueError:
                continue
        return tuple(networks)

    def peer_may_set_forwarded_for(self, peer: str | None) -> bool:
        """Whether a header from this peer should be believed at all.

        With no allow-list configured this is always true, which keeps the
        behaviour a platform deployment depends on. Once one is configured, a
        connection from anywhere else has its X-Forwarded-For ignored and is
        rate limited on the address it actually came from.
        """
        networks = self.trusted_proxy_networks
        if not networks:
            return True
        if peer is None:
            return False
        try:
            address = ip_address(peer)
        except ValueError:
            return False
        return any(address in network for network in networks)

    def production_config_errors(self) -> list[str]:
        """Configuration that must not reach a public deployment.

        Checked at startup rather than as a pydantic validator so unit tests can
        still build a Settings object cheaply, and so the message names every
        problem at once instead of failing on the first.
        """
        if self.is_development:
            return []

        errors: list[str] = []
        secret = self.jwt_secret.strip()

        if len(secret) < MIN_JWT_SECRET_LENGTH:
            errors.append(
                f"JWT_SECRET is {len(secret)} characters long; at least "
                f"{MIN_JWT_SECRET_LENGTH} are required outside development. "
                "Generate one with `openssl rand -hex 32`."
            )

        lowered = secret.lower()
        if any(marker in lowered for marker in _PLACEHOLDER_SECRET_MARKERS):
            errors.append(
                "JWT_SECRET looks like a placeholder from documentation rather "
                "than a generated secret. Anyone who can read it can sign a "
                "token for any account, including an admin. Generate one with "
                "`openssl rand -hex 32`."
            )

        return errors

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if not origins and self.is_development:
            # The web app runs on Vite's port in development while the API is
            # on this one, so local work does need cross-origin access.
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
            ]
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
