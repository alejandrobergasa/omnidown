from pathlib import Path
import tempfile

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OmniDown"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    download_dir: str = str(Path(tempfile.gettempdir()) / "omnidown-downloads")
    download_timeout_seconds: int = 180
    extract_cache_ttl_seconds: int = 900
    extract_cache_max_entries: int = 64
    max_video_height: int = 1080
    max_audio_bitrate: int = 320
    yt_dlp_cookies_file: str | None = None
    yt_dlp_cookies_from_browser: str | None = None
    yt_dlp_cookies_browser_profile: str | None = None
    yt_dlp_auto_cookies_from_browser: bool = True
    yt_dlp_browser_candidates: str = "chrome,edge,firefox,brave"
    yt_dlp_youtube_player_clients: str = ""
    yt_dlp_username: str | None = None
    yt_dlp_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
