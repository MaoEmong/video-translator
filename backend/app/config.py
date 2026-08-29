from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "video-translator"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://video:video@localhost:5432/video_translator"
    redis_url: str = "redis://localhost:6379/0"

    storage_endpoint: str | None = None
    storage_region: str = "us-east-1"
    storage_bucket: str = "video-translator"
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_upload_url_ttl_seconds: int = 900
    storage_download_url_ttl_seconds: int = 900

    openai_api_key: str | None = None
    # whisper-1 is used by default because the subtitle pipeline requires
    # verbose_json segment timestamps.
    openai_stt_model: str = "whisper-1"
    openai_translation_model: str | None = None
    openai_translation_prompt_version: str = "v1"
    openai_timeout_seconds: int = 120
    openai_max_concurrency: int = 4
    translation_batch_size: int = 20

    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"

    max_upload_size_bytes: int = 1_073_741_824

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
