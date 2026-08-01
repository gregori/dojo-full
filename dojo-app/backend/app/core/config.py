from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "mysql+pymysql://dojo_user:dojo_pass@db:3306/dojo_db"

    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Application
    debug: bool = False
    environment: str = "development"

    # Object storage (OCI Object Storage, used for document metadata-only persistence)
    documents_bucket_name: str = "dojo-documents"
    oci_bucket_namespace: str = ""
    oci_tenancy_ocid: str = ""
    oci_user_ocid: str = ""
    oci_fingerprint: str = ""
    oci_private_key: str = ""
    oci_region: str = "sa-saopaulo-1"

    # Web Push (VAPID, RFC 8292)
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
