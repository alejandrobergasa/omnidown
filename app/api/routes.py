from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.logging import get_logger
from app.core.schemas import ExtractRequest, ExtractResponse
from app.services.downloader import DownloadError, downloader_service

router = APIRouter(prefix="/api", tags=["downloads"])
logger = get_logger(__name__)


@router.post("/extract", response_model=ExtractResponse)
async def extract_formats(payload: ExtractRequest) -> ExtractResponse:
    try:
        return downloader_service.extract(str(payload.url))
    except DownloadError as exc:
        logger.warning("extract_failed url=%s error=%s", str(payload.url), str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_extract_error url=%s", str(payload.url))
        raise HTTPException(
            status_code=500,
            detail="No hemos podido analizar la URL. Intenta de nuevo en unos segundos.",
        ) from exc


@router.get("/download")
async def download_file(
    background_tasks: BackgroundTasks,
    url: str = Query(...),
    format_id: str = Query(...),
    media_type: str = Query(..., pattern="^(video|audio)$"),
    audio_format: str = Query("mp3", pattern="^(mp3|m4a|wav)$"),
):
    try:
        download = downloader_service.download(
            url=url,
            format_id=format_id,
            media_type=media_type,
            audio_format=audio_format,
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
            detail="La descarga ha fallado. Prueba con otra calidad o vuelve a intentarlo.",
        ) from exc
