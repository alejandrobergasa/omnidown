import mimetypes
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import urlparse
from uuid import uuid4

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from app.core.config import settings
from app.core.i18n import DEFAULT_LOCALE, t
from app.core.logging import get_logger
from app.core.schemas import DownloadIntentResponse, DownloadJobResponse, ExtractResponse, FormatOption

logger = get_logger(__name__)


class DownloadError(Exception):
    """Known downloader error."""


class _YtDlpLogger:
    def debug(self, _message: str) -> None:
        return

    def info(self, _message: str) -> None:
        return

    def warning(self, _message: str) -> None:
        return

    def error(self, _message: str) -> None:
        return


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


@dataclass
class DownloadJob:
    job_id: str
    url: str
    format_id: str
    media_type: str
    audio_format: str
    format_label: str
    filename: str
    status: str
    progress_percent: float
    status_text: str
    locale: str
    created_at: float
    file_path: str | None = None
    content_type: str | None = None
    temp_dir: str | None = None
    error_message: str | None = None
    expires_at: float | None = None


class DownloaderService:
    def __init__(self) -> None:
        os.makedirs(settings.download_dir, exist_ok=True)
        self._extract_cache: dict[str, CachedExtraction] = {}
        self._download_jobs: dict[str, DownloadJob] = {}
        self._cache_lock = Lock()
        self._jobs_lock = Lock()

    def extract(self, url: str, *, locale: str = DEFAULT_LOCALE) -> ExtractResponse:
        _, response = self._get_or_create_extraction(url, locale=locale)
        return response

    def download(
        self,
        *,
        url: str,
        format_id: str,
        media_type: str,
        audio_format: str,
        locale: str = DEFAULT_LOCALE,
    ) -> DownloadResult:
        _, cached_response = self._get_or_create_extraction(url, locale=locale)
        selected_option = self._get_selected_option(
            cached_response,
            format_id=format_id,
            media_type=media_type,
            locale=locale,
        )

        temp_dir = tempfile.mkdtemp(prefix="omnidown-", dir=settings.download_dir)
        safe_name = self._sanitize_filename(cached_response.title or "download")
        output_template = str(Path(temp_dir) / f"{safe_name}.%(ext)s")
        selected_format_selectors = self._build_download_selector_candidates(
            url=url,
            format_id=format_id,
            media_type=media_type,
            selected_option=selected_option,
        )

        ydl_opts = self._build_ydl_options(
            url=url,
            output_template=output_template,
            format_selector=selected_format_selectors[0],
        )

        if media_type == "audio":
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": str(settings.max_audio_bitrate),
                }
            ]

        try:
            _, final_path = self._download_with_retries(
                url=url,
                locale=locale,
                ydl_opts=ydl_opts,
                media_type=media_type,
                audio_format=audio_format,
                format_selectors=selected_format_selectors,
            )
        except DownloadError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        if not final_path.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise DownloadError(t(locale, "errors.download_missing_file"))

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
        locale: str = DEFAULT_LOCALE,
    ) -> DownloadIntentResponse:
        _, cached_response = self._get_or_create_extraction(url, locale=locale)
        selected_option = self._get_selected_option(
            cached_response,
            format_id=format_id,
            media_type=media_type,
            locale=locale,
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

    def create_download_job(
        self,
        *,
        url: str,
        format_id: str,
        media_type: str,
        audio_format: str,
        locale: str = DEFAULT_LOCALE,
    ) -> DownloadJobResponse:
        _, cached_response = self._get_or_create_extraction(url, locale=locale)
        selected_option = self._get_selected_option(
            cached_response,
            format_id=format_id,
            media_type=media_type,
            locale=locale,
        )
        extension = audio_format if media_type == "audio" else selected_option.extension
        filename = f"{self._sanitize_filename(cached_response.title or 'download')}.{extension}"
        job = DownloadJob(
            job_id=uuid4().hex,
            url=url,
            format_id=format_id,
            media_type=media_type,
            audio_format=audio_format,
            format_label=selected_option.label,
            filename=filename,
            status="pending",
            progress_percent=0.0,
            status_text=t(locale, "jobs.preparing"),
            locale=locale,
            created_at=time.time(),
        )

        with self._jobs_lock:
            self._download_jobs[job.job_id] = job

        worker = Thread(target=self._run_download_job, args=(job.job_id,), daemon=True)
        worker.start()
        return self.get_download_job(job.job_id)

    def get_download_job(
        self, job_id: str, *, locale: str = DEFAULT_LOCALE
    ) -> DownloadJobResponse:
        self._prune_expired_jobs()
        with self._jobs_lock:
            job = self._download_jobs.get(job_id)
            if not job:
                raise DownloadError(t(locale, "errors.download_unavailable"))
            return self._job_to_response(job)

    def get_downloaded_file(
        self, job_id: str, *, locale: str = DEFAULT_LOCALE
    ) -> DownloadResult:
        with self._jobs_lock:
            job = self._download_jobs.get(job_id)
            if not job:
                raise DownloadError(t(locale, "errors.download_unavailable"))
            if job.status != "completed" or not job.file_path or not job.temp_dir or not job.content_type:
                raise DownloadError(t(job.locale, "errors.download_not_ready"))
            return DownloadResult(
                file_path=job.file_path,
                filename=job.filename,
                content_type=job.content_type,
                temp_dir=job.temp_dir,
            )

    def finalize_download_job(self, job_id: str) -> None:
        with self._jobs_lock:
            self._download_jobs.pop(job_id, None)

    def get_cache_stats(self) -> dict[str, int]:
        self._prune_expired_cache()
        with self._cache_lock:
            return {
                "entries": len(self._extract_cache),
                "ttl_seconds": settings.extract_cache_ttl_seconds,
                "max_entries": settings.extract_cache_max_entries,
            }

    def get_runtime_status(self) -> dict[str, object]:
        cookies_mode = "none"
        browser_name: str | None = None
        available_browsers = self._detect_browser_cookie_sources()

        if settings.yt_dlp_cookies_file:
            cookies_mode = "cookiefile"
        elif settings.yt_dlp_cookies_from_browser:
            cookies_mode = "browser-configured"
            browser_name = settings.yt_dlp_cookies_from_browser
        elif settings.yt_dlp_auto_cookies_from_browser:
            browser_name = available_browsers[0] if available_browsers else None
            if browser_name:
                cookies_mode = "browser-auto"

        return {
            "cookies_mode": cookies_mode,
            "browser": browser_name,
            "available_browsers": available_browsers,
            "youtube_player_clients": self._split_csv(settings.yt_dlp_youtube_player_clients),
        }

    def _run_download_job(self, job_id: str) -> None:
        with self._jobs_lock:
            job = self._download_jobs.get(job_id)
            if not job:
                return

        try:
            _, cached_response = self._get_or_create_extraction(job.url, locale=job.locale)
            selected_option = self._get_selected_option(
                cached_response,
                format_id=job.format_id,
                media_type=job.media_type,
                locale=job.locale,
            )

            temp_dir = tempfile.mkdtemp(prefix="omnidown-", dir=settings.download_dir)
            safe_name = self._sanitize_filename(cached_response.title or "download")
            output_template = str(Path(temp_dir) / f"{safe_name}.%(ext)s")
            selected_format_selectors = self._build_download_selector_candidates(
                url=job.url,
                format_id=job.format_id,
                media_type=job.media_type,
                selected_option=selected_option,
            )
            self._update_job(
                job_id,
                status="downloading",
                progress_percent=0.0,
                status_text=t(job.locale, "jobs.connecting"),
            )

            with self._jobs_lock:
                stored_job = self._download_jobs.get(job_id)
                if stored_job:
                    stored_job.temp_dir = temp_dir

            def on_progress(payload: dict) -> None:
                status = payload.get("status")
                if status == "downloading":
                    downloaded = payload.get("downloaded_bytes") or 0
                    total = payload.get("total_bytes") or payload.get("total_bytes_estimate") or 0
                    percent = min(99.0, round((downloaded / total) * 100, 1)) if total else 0.0
                    speed = payload.get("speed")
                    eta = payload.get("eta")
                    parts = [f"{percent:.1f}%"]
                    if speed:
                        parts.append(t(job.locale, "jobs.speed", speed=self._to_mb(int(speed))))
                    if eta is not None:
                        parts.append(t(job.locale, "jobs.eta", seconds=int(eta)))
                    self._update_job(
                        job_id,
                        status="downloading",
                        progress_percent=percent,
                        status_text=" · ".join(parts),
                    )
                elif status == "finished":
                    self._update_job(
                        job_id,
                        status="processing",
                        progress_percent=99.0,
                        status_text=t(job.locale, "jobs.processing"),
                    )

            ydl_opts = self._build_ydl_options(
                url=job.url,
                output_template=output_template,
                format_selector=selected_format_selectors[0],
                progress_hooks=[on_progress],
            )

            if job.media_type == "audio":
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": job.audio_format,
                        "preferredquality": str(settings.max_audio_bitrate),
                    }
                ]

            _, final_path = self._download_with_retries(
                url=job.url,
                locale=job.locale,
                ydl_opts=ydl_opts,
                media_type=job.media_type,
                audio_format=job.audio_format,
                format_selectors=selected_format_selectors,
            )

            if not final_path.exists():
                raise DownloadError(t(job.locale, "errors.download_missing_file"))

            content_type = mimetypes.guess_type(final_path.name)[0] or "application/octet-stream"
            with self._jobs_lock:
                stored_job = self._download_jobs.get(job_id)
                if not stored_job:
                    return
                stored_job.file_path = str(final_path)
                stored_job.filename = final_path.name
                stored_job.content_type = content_type
                stored_job.temp_dir = temp_dir
                stored_job.status = "completed"
                stored_job.progress_percent = 100.0
                stored_job.status_text = t(stored_job.locale, "jobs.ready")
                stored_job.expires_at = time.time() + 900
        except DownloadError as exc:
            self._fail_job(job_id, str(exc))
        except Exception:  # pragma: no cover
            logger.exception("unexpected_job_download_error job_id=%s", job_id)
            self._fail_job(job_id, t(job.locale, "jobs.failed_retry"))

    def _update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress_percent: float | None = None,
        status_text: str | None = None,
    ) -> None:
        with self._jobs_lock:
            job = self._download_jobs.get(job_id)
            if not job:
                return
            if status is not None:
                job.status = status
            if progress_percent is not None:
                job.progress_percent = progress_percent
            if status_text is not None:
                job.status_text = status_text

    def _fail_job(self, job_id: str, message: str) -> None:
        with self._jobs_lock:
            job = self._download_jobs.get(job_id)
            if not job:
                return
            if job.temp_dir:
                shutil.rmtree(job.temp_dir, ignore_errors=True)
                job.temp_dir = None
            job.status = "failed"
            job.progress_percent = 0.0
            job.status_text = message
            job.error_message = message
            job.expires_at = time.time() + 300

    def _prune_expired_jobs(self) -> None:
        now = time.time()
        with self._jobs_lock:
            expired = [
                job_id
                for job_id, job in self._download_jobs.items()
                if job.expires_at is not None and job.expires_at <= now
            ]
            for job_id in expired:
                job = self._download_jobs.pop(job_id, None)
                if job and job.temp_dir:
                    shutil.rmtree(job.temp_dir, ignore_errors=True)

    @staticmethod
    def _job_to_response(job: DownloadJob) -> DownloadJobResponse:
        file_url = f"/api/download-jobs/{job.job_id}/file" if job.status == "completed" else None
        return DownloadJobResponse(
            job_id=job.job_id,
            status=job.status,
            progress_percent=job.progress_percent,
            status_text=job.status_text,
            filename=job.filename,
            media_type=job.media_type,
            format_label=job.format_label,
            file_url=file_url,
        )

    def _extract_info(self, url: str, *, locale: str) -> dict:
        opts = self._build_ydl_options(url=url, skip_download=True)
        info = self._extract_with_retries(url=url, locale=locale, ydl_opts=opts)
        if not info:
            raise DownloadError(t(locale, "errors.extract_failed"))
        return info

    def _get_or_create_extraction(self, url: str, *, locale: str) -> tuple[dict, ExtractResponse]:
        cached = self._get_cached_extraction(url)
        if cached:
            return cached.info, self._localize_extract_response(cached.response, locale=locale)

        info = self._extract_info(url, locale=locale)
        response = self._build_extract_response(url, info, locale=locale)
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
        locale: str,
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
            raise DownloadError(t(locale, "errors.invalid_format"))
        return selected_option

    def _build_extract_response(self, url: str, info: dict, *, locale: str) -> ExtractResponse:
        formats = self._build_format_options(info)
        if not formats:
            raise DownloadError(t(locale, "errors.no_formats"))

        platform = info.get("extractor_key") or info.get("extractor") or "unknown"
        duration = info.get("duration")
        return ExtractResponse(
            title=info.get("title") or "Untitled",
            source_url=url,
            platform=str(platform),
            uploader=info.get("uploader") or info.get("channel"),
            uploader_url=info.get("uploader_url") or info.get("channel_url"),
            view_count=info.get("view_count"),
            upload_date=info.get("upload_date"),
            thumbnail=info.get("thumbnail"),
            duration_seconds=int(duration) if duration is not None else None,
            formats=self._localize_format_options(formats, locale=locale),
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
        safe_audio_sources = self._collect_safe_audio_sources(info)

        for item in info.get("formats", []):
            format_id = item.get("format_id")
            ext = item.get("ext")
            height = item.get("height")
            width = item.get("width")
            fps = item.get("fps")
            vcodec = item.get("vcodec")
            acodec = item.get("acodec")
            filesize = item.get("filesize") or item.get("filesize_approx")
            protocol = str(item.get("protocol") or "")
            format_note = item.get("format_note")
            dynamic_range = item.get("dynamic_range")
            source_preference = item.get("source_preference")

            if not format_id or not ext:
                continue

            is_video = vcodec not in (None, "none")
            has_audio = acodec not in (None, "none")
            if not self._is_safe_download_candidate(
                protocol=protocol,
                format_note=format_note,
                dynamic_range=dynamic_range,
                source_preference=source_preference,
            ):
                continue

            if is_video and ext in {"mp4", "webm", "mkv"}:
                if height and height > settings.max_video_height:
                    continue
                if not has_audio and not self._can_pair_video_with_audio(
                    video_ext=ext,
                    safe_audio_sources=safe_audio_sources,
                ):
                    continue
                quality = self._build_video_quality(height, width, fps)
                key = (quality, ext, "video", "muxed" if has_audio else "split")
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
                        has_embedded_audio=has_audio,
                        filesize_mb=self._to_mb(filesize),
                        note=format_note,
                        recommended=False,
                    )
                )

            if has_audio and ext in {"m4a", "mp4", "webm"}:
                abr = item.get("abr")
                quality = f"{int(abr)} kbps" if abr else "audio"
                key = (quality, ext, "audio")
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
                        has_embedded_audio=True,
                        filesize_mb=self._to_mb(filesize),
                        note=format_note,
                        recommended=False,
                    )
                )

        formats.sort(key=self._sort_key, reverse=True)
        self._mark_recommended_formats(formats)
        return formats

    @staticmethod
    def _collect_safe_audio_sources(info: dict) -> set[str]:
        safe_exts: set[str] = set()
        for item in info.get("formats", []):
            ext = item.get("ext")
            acodec = item.get("acodec")
            vcodec = item.get("vcodec")
            protocol = str(item.get("protocol") or "")
            if not ext or ext not in {"m4a", "mp4", "webm"}:
                continue
            has_audio = acodec not in (None, "none")
            is_video = vcodec not in (None, "none")
            if not has_audio or is_video:
                continue
            if not DownloaderService._is_safe_download_candidate(
                protocol=protocol,
                format_note=item.get("format_note"),
                dynamic_range=item.get("dynamic_range"),
                source_preference=item.get("source_preference"),
            ):
                continue
            safe_exts.add(ext)
        return safe_exts

    @staticmethod
    def _can_pair_video_with_audio(*, video_ext: str, safe_audio_sources: set[str]) -> bool:
        if video_ext == "mp4":
            return "m4a" in safe_audio_sources or "mp4" in safe_audio_sources
        if video_ext == "webm":
            return "webm" in safe_audio_sources
        if video_ext == "mkv":
            return bool(safe_audio_sources)
        return False

    @staticmethod
    def _is_safe_download_candidate(
        *,
        protocol: str,
        format_note: str | None,
        dynamic_range: str | None,
        source_preference: int | None,
    ) -> bool:
        lowered_protocol = protocol.lower()
        lowered_note = (format_note or "").lower()
        lowered_range = (dynamic_range or "").lower()
        if not lowered_protocol:
            return True
        if "m3u8" in lowered_protocol or "ism" in lowered_protocol:
            return False
        if "dash" in lowered_protocol and "https" not in lowered_protocol and "http" not in lowered_protocol:
            return False
        if "drm" in lowered_note or "storyboard" in lowered_note or "images" in lowered_note:
            return False
        if lowered_range == "hdr":
            return False
        if source_preference is not None and source_preference < -1:
            return False
        return True

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

    def _localize_extract_response(self, response: ExtractResponse, *, locale: str) -> ExtractResponse:
        localized = response.model_copy(deep=True)
        localized.formats = self._localize_format_options(localized.formats, locale=locale)
        return localized

    def _localize_format_options(
        self, formats: list[FormatOption], *, locale: str
    ) -> list[FormatOption]:
        localized: list[FormatOption] = []
        for fmt in formats:
            copy = fmt.model_copy(deep=True)
            if copy.media_type == "audio":
                copy.label = t(locale, "formats.audio", quality=copy.quality, ext=copy.extension)
            else:
                has_muxed_audio = "video+audio" in copy.label
                video_only = "video only + audio" in copy.label or "solo video + audio" in copy.label
                suffix = t(
                    locale,
                    "formats.video_with_audio" if has_muxed_audio and not video_only else "formats.video_only_plus_audio",
                )
                copy.label = t(
                    locale,
                    "formats.video",
                    quality=copy.quality,
                    ext=copy.extension,
                    suffix=suffix,
                )
            localized.append(copy)
        return localized

    @staticmethod
    def _friendly_error(message: str, *, locale: str) -> str:
        lowered = message.lower()
        if "ffmpeg is not installed" in lowered or "ffprobe is not installed" in lowered:
            return t(locale, "errors.ffmpeg_missing")
        if "unsupported url" in lowered:
            return t(locale, "errors.unsupported_url")
        if "sign in to confirm you" in lowered and "not a bot" in lowered:
            return t(locale, "errors.youtube_bot_protection")
        if "private video" in lowered or "login" in lowered:
            return t(locale, "errors.private_or_login")
        if "copyright" in lowered or "unavailable" in lowered:
            return t(locale, "errors.unavailable_content")
        return t(locale, "errors.generic_processing")

    def _build_ydl_options(
        self,
        *,
        url: str | None = None,
        output_template: str | None = None,
        format_selector: str | None = None,
        skip_download: bool = False,
        progress_hooks: list | None = None,
    ) -> dict:
        opts = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": settings.download_timeout_seconds,
            "logger": _YtDlpLogger(),
        }
        if output_template is not None:
            opts["outtmpl"] = output_template
        if format_selector is not None:
            opts["format"] = format_selector
            opts["merge_output_format"] = "mp4"
        if skip_download:
            opts["skip_download"] = True
        if progress_hooks:
            opts["progress_hooks"] = progress_hooks

        if url and self._is_youtube_url(url):
            player_clients = self._split_csv(settings.yt_dlp_youtube_player_clients)
            if player_clients:
                opts["extractor_args"] = {
                    "youtube": {
                        "player_client": player_clients,
                    }
                }

        if url and self._is_tiktok_url(url):
            opts.setdefault("extractor_args", {})["tiktok"] = {
                "webpage_download": True,
            }

        if url and self._is_instagram_url(url):
            if settings.yt_dlp_username and settings.yt_dlp_password:
                opts.setdefault("extractor_args", {})["instagram"] = {
                    "username": settings.yt_dlp_username,
                    "password": settings.yt_dlp_password,
                }

        if url and self._is_facebook_url(url):
            if settings.yt_dlp_username and settings.yt_dlp_password:
                opts.setdefault("extractor_args", {})["facebook"] = {
                    "username": settings.yt_dlp_username,
                    "password": settings.yt_dlp_password,
                }

        if url and self._is_twitter_url(url):
            if settings.yt_dlp_username and settings.yt_dlp_password:
                opts.setdefault("extractor_args", {})["twitter"] = {
                    "username": settings.yt_dlp_username,
                    "password": settings.yt_dlp_password,
                }

        return opts

    def _extract_with_retries(self, *, url: str, locale: str, ydl_opts: dict) -> dict:
        last_exc: YtDlpDownloadError | None = None
        for attempt_name, attempt_opts in self._build_ydl_attempts(ydl_opts):
            try:
                with YoutubeDL(attempt_opts) as ydl:
                    return ydl.extract_info(url, download=False, process=False)
            except YtDlpDownloadError as exc:
                last_exc = exc
                if self._should_retry_ydl_attempt(attempt_name, str(exc)):
                    logger.warning(
                        "yt_dlp_extract_attempt_failed url=%s attempt=%s error=%s",
                        url,
                        attempt_name,
                        str(exc),
                    )
                    continue
                raise DownloadError(self._friendly_error(str(exc), locale=locale)) from exc

        if last_exc is not None:
            raise DownloadError(self._friendly_error(str(last_exc), locale=locale)) from last_exc
        raise DownloadError(t(locale, "errors.extract_failed"))

    def _download_with_retries(
        self,
        *,
        url: str,
        locale: str,
        ydl_opts: dict,
        media_type: str,
        audio_format: str,
        format_selectors: list[str],
    ) -> tuple[dict, Path]:
        last_exc: YtDlpDownloadError | None = None
        for selector_index, format_selector in enumerate(format_selectors):
            for attempt_name, attempt_opts in self._build_ydl_attempts(ydl_opts):
                attempt_opts["format"] = format_selector
                try:
                    with YoutubeDL(attempt_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        final_path = Path(ydl.prepare_filename(info))
                        if media_type == "audio":
                            final_path = final_path.with_suffix(f".{audio_format}")
                        elif (
                            final_path.suffix.lower() != ".mp4"
                            and final_path.with_suffix(".mp4").exists()
                        ):
                            final_path = final_path.with_suffix(".mp4")
                        return info, final_path
                except YtDlpDownloadError as exc:
                    last_exc = exc
                    if selector_index < len(format_selectors) - 1 and self._looks_like_auth_or_bot_block(str(exc).lower()):
                        logger.warning(
                            "yt_dlp_download_selector_fallback url=%s selector=%s next_selector=%s error=%s",
                            url,
                            format_selector,
                            format_selectors[selector_index + 1],
                            str(exc),
                        )
                        break
                    if self._should_retry_ydl_attempt(attempt_name, str(exc)):
                        logger.warning(
                            "yt_dlp_download_attempt_failed url=%s attempt=%s error=%s",
                            url,
                            attempt_name,
                            str(exc),
                        )
                        continue
                    raise DownloadError(self._friendly_error(str(exc), locale=locale)) from exc

        if last_exc is not None:
            raise DownloadError(self._friendly_error(str(last_exc), locale=locale)) from last_exc
        raise DownloadError(t(locale, "errors.download_failed"))

    def _build_ydl_attempts(self, base_opts: dict) -> list[tuple[str, dict]]:
        attempts: list[tuple[str, dict]] = [("plain", dict(base_opts))]
        for attempt_name, cookie_opts in self._resolve_cookie_attempts():
            attempt_opts = dict(base_opts)
            attempt_opts.update(cookie_opts)
            attempts.append((attempt_name, attempt_opts))
        return attempts

    @staticmethod
    def _should_retry_ydl_attempt(attempt_name: str, error_message: str) -> bool:
        lowered = error_message.lower()
        if attempt_name == "plain":
            return DownloaderService._looks_like_auth_or_bot_block(lowered)
        if "could not copy" in lowered or "failed to decrypt with dpapi" in lowered:
            return True
        return DownloaderService._looks_like_auth_or_bot_block(lowered)

    @staticmethod
    def _looks_like_auth_or_bot_block(lowered_error: str) -> bool:
        return any(
            token in lowered_error
            for token in (
                "sign in to confirm",
                "not a bot",
                "authentication",
                "requires authentication",
                "login",
                "private video",
                "cookies",
                "age-restricted",
            )
        )

    def _resolve_cookie_attempts(self) -> list[tuple[str, dict]]:
        attempts: list[tuple[str, dict]] = []
        if settings.yt_dlp_cookies_file:
            attempts.append(("cookiefile", {"cookiefile": settings.yt_dlp_cookies_file}))

        if settings.yt_dlp_cookies_from_browser:
            browser_spec = [settings.yt_dlp_cookies_from_browser]
            if settings.yt_dlp_cookies_browser_profile:
                browser_spec.append(settings.yt_dlp_cookies_browser_profile)
            attempts.append(
                (
                    f"browser:{settings.yt_dlp_cookies_from_browser}",
                    {"cookiesfrombrowser": tuple(browser_spec)},
                )
            )

        if settings.yt_dlp_auto_cookies_from_browser:
            for browser_name in self._detect_browser_cookie_sources():
                attempts.append(
                    (
                        f"browser-auto:{browser_name}",
                        {"cookiesfrombrowser": (browser_name,)},
                    )
                )

        if settings.yt_dlp_username and settings.yt_dlp_password:
            attempts.append(
                (
                    "credentials",
                    {"username": settings.yt_dlp_username, "password": settings.yt_dlp_password},
                )
            )

        return attempts

    @staticmethod
    def _detect_browser_cookie_source() -> str | None:
        sources = DownloaderService._detect_browser_cookie_sources()
        return sources[0] if sources else None

    @staticmethod
    def _detect_browser_cookie_sources() -> list[str]:
        candidates = DownloaderService._split_csv(settings.yt_dlp_browser_candidates)
        if not candidates:
            return []

        local_appdata = os.environ.get("LOCALAPPDATA", "")
        roaming_appdata = os.environ.get("APPDATA", "")
        home = str(Path.home())

        browser_paths = {
            "chrome": [
                Path(local_appdata) / "Google" / "Chrome" / "User Data",
                Path(home) / ".config" / "google-chrome",
            ],
            "edge": [
                Path(local_appdata) / "Microsoft" / "Edge" / "User Data",
                Path(home) / ".config" / "microsoft-edge",
            ],
            "firefox": [
                Path(roaming_appdata) / "Mozilla" / "Firefox" / "Profiles",
                Path(home) / ".mozilla" / "firefox",
            ],
            "brave": [
                Path(local_appdata) / "BraveSoftware" / "Brave-Browser" / "User Data",
                Path(home) / ".config" / "BraveSoftware" / "Brave-Browser",
            ],
        }

        detected: list[str] = []
        for browser_name in candidates:
            for candidate_path in browser_paths.get(browser_name, []):
                if str(candidate_path) and candidate_path.exists():
                    detected.append(browser_name)
                    break
        return detected

    @staticmethod
    def _is_youtube_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return hostname in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
        }

    @staticmethod
    def _is_tiktok_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return hostname in {"tiktok.com", "www.tiktok.com", "vm.tiktok.com"}

    @staticmethod
    def _is_instagram_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return hostname in {"instagram.com", "www.instagram.com"}

    @staticmethod
    def _is_facebook_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return hostname in {"facebook.com", "www.facebook.com", "fb.com", "m.facebook.com"}

    @staticmethod
    def _is_twitter_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return hostname in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}

    @staticmethod
    def _split_csv(value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

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

    def _build_download_selector_candidates(
        self,
        *,
        url: str,
        format_id: str,
        media_type: str,
        selected_option: FormatOption,
    ) -> list[str]:
        selectors = [
            self._parse_download_selector(
                format_id=format_id,
                media_type=media_type,
                has_embedded_audio=selected_option.has_embedded_audio,
            )
        ]

        if self._is_youtube_url(url) and media_type == "video" and not selected_option.has_embedded_audio:
            selectors.extend(
                [
                    "best[ext=mp4][acodec!=none][vcodec!=none]/best[acodec!=none][vcodec!=none]",
                    "18/best[ext=mp4][acodec!=none][vcodec!=none]/best[acodec!=none][vcodec!=none]",
                ]
            )

        unique_selectors: list[str] = []
        for selector in selectors:
            if selector not in unique_selectors:
                unique_selectors.append(selector)
        return unique_selectors

    @staticmethod
    def _parse_download_selector(format_id: str, media_type: str, has_embedded_audio: bool) -> str:
        if media_type == "audio":
            return format_id

        if has_embedded_audio:
            return format_id

        # For platforms like YouTube, higher resolutions are often video-only.
        # We merge the chosen video stream with the best compatible audio stream.
        return f"{format_id}+bestaudio/best"


downloader_service = DownloaderService()
