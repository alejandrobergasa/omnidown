import mimetypes
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.schemas import ExtractResponse, FormatOption

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


class DownloaderService:
    def __init__(self) -> None:
        os.makedirs(settings.download_dir, exist_ok=True)

    def extract(self, url: str) -> ExtractResponse:
        info = self._extract_info(url)
        formats = self._build_format_options(info)
        if not formats:
            raise DownloadError("No se han encontrado formatos descargables para esta URL.")

        platform = info.get("extractor_key") or info.get("extractor") or "unknown"
        return ExtractResponse(
            title=info.get("title") or "Untitled",
            source_url=url,
            platform=str(platform),
            thumbnail=info.get("thumbnail"),
            duration_seconds=info.get("duration"),
            formats=formats,
        )

    def download(
        self,
        *,
        url: str,
        format_id: str,
        media_type: str,
        audio_format: str,
    ) -> DownloadResult:
        temp_dir = tempfile.mkdtemp(prefix="omnidown-", dir=settings.download_dir)
        safe_name = self._sanitize_filename(self._extract_info(url).get("title") or "download")
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
                    )
                )

        formats.sort(key=self._sort_key, reverse=True)
        return formats

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
