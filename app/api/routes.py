from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.core.i18n import get_request_locale, t
from app.core.logging import get_logger
from app.core.schemas import (
    DownloadIntentResponse,
    DownloadJobResponse,
    DownloadRequest,
    ExtractRequest,
    ExtractResponse,
)
from app.services.downloader import DownloadError, downloader_service

router = APIRouter(prefix="/api", tags=["downloads"])
logger = get_logger(__name__)


@router.post("/extract", response_model=ExtractResponse)
async def extract_formats(payload: ExtractRequest, request: Request) -> ExtractResponse:
    locale = get_request_locale(request)
    try:
        return downloader_service.extract(str(payload.url), locale=locale)
    except DownloadError as exc:
        logger.warning("extract_failed url=%s error=%s", str(payload.url), str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_extract_error url=%s", str(payload.url))
        raise HTTPException(
            status_code=500,
            detail=t(locale, "errors.analyze_unexpected"),
        ) from exc


@router.post("/download-intent", response_model=DownloadIntentResponse)
async def prepare_download(payload: DownloadRequest, request: Request) -> DownloadIntentResponse:
    locale = get_request_locale(request)
    try:
        return downloader_service.prepare_download(
            url=str(payload.url),
            format_id=payload.format_id,
            media_type=payload.media_type,
            audio_format=payload.audio_format,
            locale=locale,
        )
    except DownloadError as exc:
        logger.warning(
            "prepare_download_failed url=%s format_id=%s media_type=%s error=%s",
            str(payload.url),
            payload.format_id,
            payload.media_type,
            str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_prepare_download_error url=%s", str(payload.url))
        raise HTTPException(
            status_code=500,
            detail=t(locale, "errors.prepare_download_unexpected"),
        ) from exc


@router.post("/download-jobs", response_model=DownloadJobResponse)
async def create_download_job(payload: DownloadRequest, request: Request) -> DownloadJobResponse:
    locale = get_request_locale(request)
    try:
        return downloader_service.create_download_job(
            url=str(payload.url),
            format_id=payload.format_id,
            media_type=payload.media_type,
            audio_format=payload.audio_format,
            locale=locale,
        )
    except DownloadError as exc:
        logger.warning(
            "create_download_job_failed url=%s format_id=%s media_type=%s error=%s",
            str(payload.url),
            payload.format_id,
            payload.media_type,
            str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_create_download_job_error url=%s", str(payload.url))
        raise HTTPException(
            status_code=500,
            detail=t(locale, "errors.create_download_unexpected"),
        ) from exc


@router.get("/download-jobs/{job_id}", response_model=DownloadJobResponse)
async def get_download_job(job_id: str, request: Request) -> DownloadJobResponse:
    locale = get_request_locale(request)
    try:
        return downloader_service.get_download_job(job_id, locale=locale)
    except DownloadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/download-jobs/{job_id}/file")
async def download_job_file(job_id: str, background_tasks: BackgroundTasks, request: Request):
    locale = get_request_locale(request)
    try:
        download = downloader_service.get_downloaded_file(job_id, locale=locale)
        background_tasks.add_task(download.cleanup)
        background_tasks.add_task(downloader_service.finalize_download_job, job_id)
        return FileResponse(
            path=download.file_path,
            media_type=download.content_type,
            filename=download.filename,
        )
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/download")
async def download_file(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Query(...),
    format_id: str = Query(...),
    media_type: str = Query(..., pattern="^(video|audio)$"),
    audio_format: str = Query("mp3", pattern="^(mp3|m4a|wav)$"),
):
    locale = get_request_locale(request)
    try:
        download = downloader_service.download(
            url=url,
            format_id=format_id,
            media_type=media_type,
            audio_format=audio_format,
            locale=locale,
        )
        background_tasks.add_task(download.cleanup)
        return FileResponse(
            path=download.file_path,
            media_type=download.content_type,
            filename=download.filename,
        )
    except DownloadError as exc:
        logger.warning(
            "download_failed url=%s format_id=%s media_type=%s error=%s",
            url,
            format_id,
            media_type,
            str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_download_error url=%s format_id=%s", url, format_id)
        raise HTTPException(
            status_code=500,
            detail=t(locale, "errors.download_failed"),
        ) from exc


@router.get("/system-status")
async def system_status():
    return {
        "status": "ok",
        "cache": downloader_service.get_cache_stats(),
        "runtime": downloader_service.get_runtime_status(),
    }
