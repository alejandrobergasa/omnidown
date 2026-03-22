from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from yt_dlp import YoutubeDL

from app.core.config import settings
from app.services.downloader import DownloadError, downloader_service


DEFAULT_CASES = {
    "youtube": "https://www.youtube.com/watch?v=hWop9c8ogHY",
    "tiktok": "https://www.tiktok.com/@patroxofficial/video/6742501081818877190?langCountry=en",
    "instagram": "https://www.instagram.com/reel/Chunk8-jurw/",
    "facebook": "https://www.facebook.com/cnn/videos/10155529876156509/",
    "twitter": "https://twitter.com/i/web/status/910031516746514432",
}


@dataclass
class ValidationResult:
    platform: str
    url: str
    extract_ok: bool
    download_ok: bool
    extract_error: str | None = None
    download_error: str | None = None
    selected_format_id: str | None = None
    selected_format_label: str | None = None
    output_filename: str | None = None
    output_content_type: str | None = None
    output_size: int | None = None
    formats_count: int = 0
    title: str | None = None
    debug: dict | None = None


def _pick_format(response):
    recommended_video = next(
        (fmt for fmt in response.formats if fmt.media_type == "video" and fmt.recommended),
        None,
    )
    if recommended_video:
        return recommended_video
    return next((fmt for fmt in response.formats if fmt.media_type == "video"), None)


def _debug_download_probe(url: str, selected, *, locale: str) -> dict:
    debug: dict[str, object] = {
        "selectors": [],
        "processed_format_ids": [],
        "attempts": [],
    }
    try:
        opts = downloader_service._build_ydl_options(url=url, skip_download=True)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        debug["processed_format_ids"] = [
            item.get("format_id")
            for item in (info.get("formats") or [])
            if item.get("format_id")
        ]
    except Exception as exc:  # pragma: no cover - debug helper
        debug["processed_extract_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    selectors = downloader_service._build_download_selector_candidates(
        url=url,
        format_id=selected.format_id,
        media_type=selected.media_type,
        selected_option=selected,
    )
    debug["selectors"] = selectors

    temp_dir = tempfile.mkdtemp(prefix="omnidown-debug-", dir=settings.download_dir)
    output_template = str(Path(temp_dir) / "debug.%(ext)s")
    try:
        base_opts = downloader_service._build_ydl_options(
            url=url,
            output_template=output_template,
            format_selector=selectors[0],
        )
        for selector in selectors:
            for attempt_name, attempt_opts in downloader_service._build_ydl_attempts(base_opts):
                current_opts = dict(attempt_opts)
                current_opts["format"] = selector
                try:
                    with YoutubeDL(current_opts) as ydl:
                        ydl.extract_info(url, download=True)
                    debug["attempts"].append(
                        {
                            "selector": selector,
                            "attempt": attempt_name,
                            "ok": True,
                        }
                    )
                    return debug
                except Exception as exc:  # pragma: no cover - debug helper
                    debug["attempts"].append(
                        {
                            "selector": selector,
                            "attempt": attempt_name,
                            "ok": False,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return debug


def _debug_extract_probe(url: str, *, locale: str) -> dict:
    debug: dict[str, object] = {
        "attempts": [],
    }
    ydl_opts = downloader_service._build_ydl_options(url=url, skip_download=True)
    for attempt_name, attempt_opts in downloader_service._build_ydl_attempts(ydl_opts):
        try:
            with YoutubeDL(attempt_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            debug["attempts"].append(
                {
                    "attempt": attempt_name,
                    "ok": True,
                    "extractor": info.get("extractor_key") or info.get("extractor"),
                    "title": info.get("title"),
                    "raw_format_count": len(info.get("formats") or []),
                    "raw_format_sample": [
                        {
                            "format_id": item.get("format_id"),
                            "ext": item.get("ext"),
                            "protocol": item.get("protocol"),
                            "width": item.get("width"),
                            "height": item.get("height"),
                            "vcodec": item.get("vcodec"),
                            "acodec": item.get("acodec"),
                            "source_preference": item.get("source_preference"),
                            "format_note": item.get("format_note"),
                        }
                        for item in (info.get("formats") or [])[:12]
                    ],
                    "service_format_count": len(downloader_service._build_format_options(info)),
                    "service_format_sample": [
                        {
                            "format_id": item.format_id,
                            "label": item.label,
                            "media_type": item.media_type,
                            "extension": item.extension,
                            "quality": item.quality,
                        }
                        for item in downloader_service._build_format_options(info)[:12]
                    ],
                }
            )
            return debug
        except Exception as exc:  # pragma: no cover - debug helper
            debug["attempts"].append(
                {
                    "attempt": attempt_name,
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    return debug


def validate_case(platform: str, url: str, *, locale: str, debug: bool = False) -> ValidationResult:
    result = ValidationResult(
        platform=platform,
        url=url,
        extract_ok=False,
        download_ok=False,
    )

    try:
        response = downloader_service.extract(url, locale=locale)
        result.extract_ok = True
        result.formats_count = len(response.formats)
        result.title = response.title
    except DownloadError as exc:
        result.extract_error = str(exc)
        if debug:
            result.debug = _debug_extract_probe(url, locale=locale)
        return result

    selected = _pick_format(response)
    if not selected:
        result.download_error = "No video format available"
        return result

    result.selected_format_id = selected.format_id
    result.selected_format_label = selected.label

    download = None
    try:
        download = downloader_service.download(
            url=url,
            format_id=selected.format_id,
            media_type=selected.media_type,
            audio_format="mp3",
            locale=locale,
        )
        result.download_ok = True
        result.output_filename = download.filename
        result.output_content_type = download.content_type
        with open(download.file_path, "rb") as file_obj:
            file_obj.seek(0, 2)
            result.output_size = file_obj.tell()
    except DownloadError as exc:
        result.download_error = str(exc)
    finally:
        if download is not None:
            download.cleanup()

    if debug and not result.download_ok:
        result.debug = _debug_download_probe(url, selected, locale=locale)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate supported site extraction and downloads")
    parser.add_argument("--locale", default="es")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--platform",
        action="append",
        choices=sorted(DEFAULT_CASES.keys()),
        help="Validate only the selected platform. Can be passed multiple times.",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override a default URL with platform=url. Can be passed multiple times.",
    )
    args = parser.parse_args()

    cases = dict(DEFAULT_CASES)
    for item in args.override:
        platform, separator, url = item.partition("=")
        if separator != "=" or platform not in cases or not url:
            raise SystemExit(f"Invalid --override value: {item}")
        cases[platform] = url

    selected_platforms = args.platform or list(cases.keys())
    results = [
        validate_case(platform, cases[platform], locale=args.locale, debug=args.debug)
        for platform in selected_platforms
    ]
    payload = {
        "results": [asdict(item) for item in results],
        "all_extract_ok": all(item.extract_ok for item in results),
        "all_download_ok": all(item.download_ok for item in results),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["all_download_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
