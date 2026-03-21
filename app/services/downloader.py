import mimetypes
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.schemas import DownloadIntentResponse, ExtractResponse, FormatOption

logger = get_logger(__name__)


class DownloadError(Exception):
    """Known downloader error."""


@dataclass
class DownloadResult:
    file_path: str
    filename: str
    content_type: str
    temp_dir: str

    def cleanup(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)


@dataclass
class CachedExtraction:
    info: dict
    response: ExtractResponse
    expires_at: float


class DownloaderService:
    def __init__(self) -> None:
        os.makedirs(settings.download_dir, exist_ok=True)
        self._extract_cache: dict[str, CachedExtraction] = {}
        self._cache_lock = Lock()

    def extract(self, url: str) -> ExtractResponse:
        _, response = self._get_or_create_extraction(url)
        return response

    def download(
        self,
        *,
        url: str,
        format_id: str,
        media_type: str,
        audio_format: str,
    ) -> DownloadResult:
        _, cached_response = self._get_or_create_extraction(url)
        self._get_selected_option(
            cached_response,
            format_id=format_id,
            media_type=media_type,
        )

        temp_dir = tempfile.mkdtemp(prefix="omnidown-", dir=settings.download_dir)
        safe_name = self._sanitize_filename(cached_response.title or "download")
        output_template = str(Path(temp_dir) / f"{safe_name}.%(ext)s")
        selected_format = self._parse_download_selector(format_id, media_type)

        ydl_opts = {
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": settings.download_timeout_seconds,
            "format": selected_format,
            "merge_output_format": "mp4",
        }

        if media_type == "audio":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": str(settings.max_audio_bitrate),
                }
            ]

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                final_path = Path(ydl.prepare_filename(info))

                if media_type == "audio":
                    final_path = final_path.with_suffix(f".{audio_format}")
                elif final_path.suffix.lower() != ".mp4" and final_path.with_suffix(".mp4").exists():
                    final_path = final_path.with_suffix(".mp4")
        except YtDlpDownloadError as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise DownloadError(self._friendly_error(str(exc))) from exc

        if not final_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise DownloadError("La descarga terminó sin generar archivo final.")

        content_type = mimetypes.guess_type(final_path.name)[0] or "application/octet-stream"
        return DownloadResult(
            file_path=str(final_path),
            filename=final_path.name,
            content_type=content_type,
            temp_dir=temp_dir,
        )

    def prepare_download(
        self,
        *,
        url: str,
        format_id: str,
        media_type: str,
        audio_format: str,
    ) -> DownloadIntentResponse:
        _, cached_response = self._get_or_create_extraction(url)
        selected_option = self._get_selected_option(
            cached_response,
            format_id=format_id,
            media_type=media_type,
        )
        extension = audio_format if media_type == "audio" else selected_option.extension
        filename = f"{self._sanitize_filename(cached_response.title or 'download')}.{extension}"
        return DownloadIntentResponse(
            filename=filename,
            download_url=(
                f"/api/download?url={self._quote(url)}&format_id={self._quote(format_id)}"
                f"&media_type={self._quote(media_type)}&audio_format={self._quote(audio_format)}"
            ),
            media_type=selected_option.media_type,
            format_label=selected_option.label,
        )

    def get_cache_stats(self) -> dict[str, int]:
        self._prune_expired_cache()
        with self._cache_lock:
            return {
                "entries": len(self._extract_cache),
                "ttl_seconds": settings.extract_cache_ttl_seconds,
                "max_entries": settings.extract_cache_max_entries,
            }

    def _extract_info(self, url: str) -> dict:
        opts = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": settings.download_timeout_seconds,
            "skip_download": True,
        }
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except YtDlpDownloadError as exc:
            raise DownloadError(self._friendly_error(str(exc))) from exc
        if not info:
            raise DownloadError("No se ha podido resolver la URL proporcionada.")
        return info

    def _get_or_create_extraction(self, url: str) -> tuple[dict, ExtractResponse]:
        cached = self._get_cached_extraction(url)
        if cached:
            return cached.info, cached.response.model_copy(deep=True)

        info = self._extract_info(url)
        response = self._build_extract_response(url, info)
        self._store_cached_extraction(url, info, response)
        return info, response.model_copy(deep=True)

    @staticmethod
    def _quote(value: str) -> str:
        from urllib.parse import quote

        return quote(value, safe="")

    @staticmethod
    def _get_selected_option(
        response: ExtractResponse,
        *,
        format_id: str,
        media_type: str,
    ) -> FormatOption:
        selected_option = next(
            (
                fmt
                for fmt in response.formats
                if fmt.format_id == format_id and fmt.media_type == media_type
            ),
            None,
        )
        if not selected_option:
            raise DownloadError("El formato elegido ya no es valido. Analiza la URL de nuevo.")
        return selected_option

    def _build_extract_response(self, url: str, info: dict) -> ExtractResponse:
        formats = self._build_format_options(info)
        if not formats:
            raise DownloadError("No se han encontrado formatos descargables para esta URL.")

        platform = info.get("extractor_key") or info.get("extractor") or "unknown"
        return ExtractResponse(
            title=info.get("title") or "Untitled",
            source_url=url,
            platform=str(platform),
            uploader=info.get("uploader") or info.get("channel"),
            uploader_url=info.get("uploader_url") or info.get("channel_url"),
            view_count=info.get("view_count"),
            upload_date=info.get("upload_date"),
            thumbnail=info.get("thumbnail"),
            duration_seconds=info.get("duration"),
            formats=formats,
        )

    def _get_cached_extraction(self, url: str) -> CachedExtraction | None:
        self._prune_expired_cache()
        with self._cache_lock:
            cached = self._extract_cache.get(url)
            if not cached:
                return None
            if cached.expires_at <= time.time():
                self._extract_cache.pop(url, None)
                return None
            return cached

    def _store_cached_extraction(self, url: str, info: dict, response: ExtractResponse) -> None:
        expires_at = time.time() + settings.extract_cache_ttl_seconds
        with self._cache_lock:
            self._extract_cache[url] = CachedExtraction(
                info=info,
                response=response.model_copy(deep=True),
                expires_at=expires_at,
            )
            self._trim_cache_unlocked()

    def _prune_expired_cache(self) -> None:
        now = time.time()
        with self._cache_lock:
            expired_urls = [
                url for url, cached in self._extract_cache.items() if cached.expires_at <= now
            ]
            for url in expired_urls:
                self._extract_cache.pop(url, None)

    def _trim_cache_unlocked(self) -> None:
        if len(self._extract_cache) <= settings.extract_cache_max_entries:
            return

        overflow = len(self._extract_cache) - settings.extract_cache_max_entries
        oldest_urls = sorted(
            self._extract_cache.items(),
            key=lambda item: item[1].expires_at,
        )[:overflow]
        for url, _ in oldest_urls:
            self._extract_cache.pop(url, None)

    def _build_format_options(self, info: dict) -> list[FormatOption]:
        formats: list[FormatOption] = []
        seen: set[tuple[str, str]] = set()

        for item in info.get("formats", []):
            format_id = item.get("format_id")
            ext = item.get("ext")
            height = item.get("height")
            width = item.get("width")
            fps = item.get("fps")
            vcodec = item.get("vcodec")
            acodec = item.get("acodec")
            filesize = item.get("filesize") or item.get("filesize_approx")

            if not format_id or not ext:
                continue

            is_video = vcodec not in (None, "none")
            has_audio = acodec not in (None, "none")

            if is_video and ext in {"mp4", "webm", "mkv"}:
                if height and height > settings.max_video_height:
                    continue
                quality = self._build_video_quality(height, width, fps)
                key = (format_id, "video")
                if key in seen:
                    continue
                seen.add(key)
                label_suffix = "video+audio" if has_audio else "video only + audio"
                formats.append(
                    FormatOption(
                        format_id=format_id,
                        label=f"Video {quality} ({ext}, {label_suffix})",
                        extension=ext,
                        quality=quality,
                        media_type="video",
                        filesize_mb=self._to_mb(filesize),
                        note=item.get("format_note"),
                        recommended=False,
                    )
                )

            if has_audio and ext in {"m4a", "mp4", "webm"}:
                abr = item.get("abr")
                quality = f"{int(abr)} kbps" if abr else "audio"
                key = (format_id, "audio")
                if key in seen:
                    continue
                seen.add(key)
                formats.append(
                    FormatOption(
                        format_id=format_id,
                        label=f"Audio {quality} ({ext})",
                        extension=ext,
                        quality=quality,
                        media_type="audio",
                        filesize_mb=self._to_mb(filesize),
                        note=item.get("format_note"),
                        recommended=False,
                    )
                )

        formats.sort(key=self._sort_key, reverse=True)
        self._mark_recommended_formats(formats)
        return formats

    @staticmethod
    def _mark_recommended_formats(formats: list[FormatOption]) -> None:
        preferred_video = next(
            (
                fmt
                for fmt in formats
                if fmt.media_type == "video"
                and fmt.extension == "mp4"
                and DownloaderService._quality_rank(fmt.quality) <= 1080
            ),
            None,
        )
        preferred_audio = next(
            (
                fmt
                for fmt in formats
                if fmt.media_type == "audio" and fmt.extension in {"m4a", "mp4", "webm"}
            ),
            None,
        )

        if preferred_video:
            preferred_video.recommended = True
        elif formats:
            formats[0].recommended = True

        if preferred_audio:
            preferred_audio.recommended = True

    @staticmethod
    def _friendly_error(message: str) -> str:
        lowered = message.lower()
        if "ffmpeg is not installed" in lowered or "ffprobe is not installed" in lowered:
            return (
                "Falta ffmpeg en el sistema. Instala ffmpeg y anadelo al PATH para poder "
                "fusionar video y audio o convertir a MP3."
            )
        if "unsupported url" in lowered:
            return "La URL no pertenece a una plataforma soportada por el motor de descarga."
        if "private video" in lowered or "login" in lowered:
            return "El contenido parece privado o requiere autenticación."
        if "copyright" in lowered or "unavailable" in lowered:
            return "El contenido no está disponible para descarga en este momento."
        return "No hemos podido procesar la URL indicada."

    @staticmethod
    def _sanitize_filename(value: str) -> str:
        cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.ASCII).strip()
        cleaned = re.sub(r"[-\s]+", "-", cleaned)
        return cleaned[:80] or "download"

    @staticmethod
    def _to_mb(filesize: int | None) -> float | None:
        if not filesize:
            return None
        return round(filesize / (1024 * 1024), 1)

    @staticmethod
    def _quality_rank(quality: str) -> int:
        match = re.search(r"(\d+)", quality)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _build_video_quality(height: int | None, width: int | None, fps: int | float | None) -> str:
        quality = f"{height}p" if height else "video"
        if width and height:
            quality = f"{quality} {width}x{height}"
        if fps:
            quality = f"{quality} {int(fps)}fps"
        return quality

    @staticmethod
    def _sort_key(fmt: FormatOption) -> tuple[int, int]:
        media_rank = 1 if fmt.media_type == "video" else 0
        return (media_rank, DownloaderService._quality_rank(fmt.quality))

    @staticmethod
    def _parse_download_selector(format_id: str, media_type: str) -> str:
        if media_type == "audio":
            return format_id

        # For platforms like YouTube, higher resolutions are often video-only.
        # We merge the chosen video stream with the best compatible audio stream.
        return f"{format_id}+bestaudio/best"


downloader_service = DownloaderService()
