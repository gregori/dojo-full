from pydantic_settings import BaseSettings

# Known insecure placeholder values that must never be used in production
_INSECURE_JWT_SECRETS = {
    "change-me-to-a-random-256-bit-string",
    "",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost:3306/dojo"

    # JWT
    JWT_SECRET: str = "change-me-to-a-random-256-bit-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = (
        "http://localhost:8000/api/v1/auth/google/callback"
    )

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:80"

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "5/minute"

    # App
    APP_ENV: str = "development"
    API_PREFIX: str = "/api/v1"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def model_post_init(self, __context: object) -> None:
        """Validate critical security settings after initialization."""
        # H1: Reject known insecure JWT_SECRET defaults and placeholders
        if (
            self.JWT_SECRET in _INSECURE_JWT_SECRETS
            or self.JWT_SECRET.upper().startswith("CHANGE_ME")
        ):
            msg = (
                "JWT_SECRET must be set to a strong random value via the JWT_SECRET "
                "environment variable. The current value is insecure and would allow "
                'token forgery. Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
            raise ValueError(msg)
        if len(self.JWT_SECRET) < 32:
            msg = f"JWT_SECRET must be at least 32 characters for HS256, got {len(self.JWT_SECRET)}"
            raise ValueError(msg)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
