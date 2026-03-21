from typing import Literal

from pydantic import BaseModel, HttpUrl


class ExtractRequest(BaseModel):
    url: HttpUrl


class DownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str
    media_type: Literal["video", "audio"]
    audio_format: Literal["mp3", "m4a", "wav"] = "mp3"


class FormatOption(BaseModel):
    format_id: str
    label: str
    extension: str
    quality: str
    media_type: Literal["video", "audio"]
    filesize_mb: float | None = None
    note: str | None = None
    recommended: bool = False


class ExtractResponse(BaseModel):
    title: str
    source_url: str
    platform: str
    uploader: str | None = None
    uploader_url: str | None = None
    view_count: int | None = None
    upload_date: str | None = None
    thumbnail: str | None = None
    duration_seconds: int | None = None
    formats: list[FormatOption]


class DownloadIntentResponse(BaseModel):
    filename: str
    download_url: str
    media_type: Literal["video", "audio"]
    format_label: str
