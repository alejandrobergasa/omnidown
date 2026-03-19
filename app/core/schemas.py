from typing import Literal

from pydantic import BaseModel, HttpUrl


class ExtractRequest(BaseModel):
    url: HttpUrl


class FormatOption(BaseModel):
    format_id: str
    label: str
    extension: str
    quality: str
    media_type: Literal["video", "audio"]
    filesize_mb: float | None = None
    note: str | None = None


class ExtractResponse(BaseModel):
    title: str
    source_url: str
    platform: str
    thumbnail: str | None = None
    duration_seconds: int | None = None
    formats: list[FormatOption]
