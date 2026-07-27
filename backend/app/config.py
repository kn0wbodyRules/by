from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 5

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@boqtool.local"
    # Bounded so a blocked SMTP port (common on campus/ISP networks, which firewall
    # ports 25/465/587) fails fast instead of hanging the request for minutes.
    SMTP_TIMEOUT_SECONDS: int = 10

    # OAuth sign-in (Google, GitHub).
    # Leave the client id/secret blank to keep a provider mocked; OAUTH_MOCK_MODE
    # forces mocking for every provider. Mock sign-in is refused in production.
    # Force the built-in mock provider even when credentials exist (useful for
    # tests). Leaving this false still falls back to mocking any provider whose
    # client id/secret is blank — so adding real credentials is enough to go
    # live, without also remembering to flip a flag.
    OAUTH_MOCK_MODE: bool = False
    # Must match the redirect URI registered in each provider's developer console:
    #   <base>/auth/oauth/google/callback   and   <base>/auth/oauth/github/callback
    OAUTH_REDIRECT_BASE: str = "http://127.0.0.1:8000"
    # Where the backend sends the browser once a token has been issued.
    OAUTH_SUCCESS_REDIRECT: str = "http://localhost:5173/auth/callback"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # Gemini Vision
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_MOCK_MODE: bool = True

    # Stage 2b — Gemini embedding room-type classifier (escalation layer).
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"
    ROOM_EMBED_DIM: int = 768
    # Below this cosine similarity to the nearest reference phrase, the embedding
    # guess is not trusted and the room stays OTHER — same "don't guess when unsure"
    # gate as the correction-factor confidence logic. Calibrated against real
    # gemini-embedding-001 output (tools/calibrate_room_embed.py): genuine creative
    # room names scored >=0.887, non-rooms (garden, staircase, parking) <=0.865, so
    # 0.88 cleanly separates them while defaulting the uncertain middle to OTHER.
    ROOM_EMBED_MATCH_THRESHOLD: float = 0.88

    # App
    ENV: str = "development"
    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
