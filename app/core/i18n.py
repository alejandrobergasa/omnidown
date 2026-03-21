from __future__ import annotations

from fastapi import Request

SUPPORTED_LOCALES = {"es", "en"}
DEFAULT_LOCALE = "en"

TRANSLATIONS = {
    "es": {
        "errors.analyze_unexpected": "No hemos podido analizar la URL. Intenta de nuevo en unos segundos.",
        "errors.prepare_download_unexpected": "No hemos podido preparar la descarga. Intenta de nuevo.",
        "errors.create_download_unexpected": "No hemos podido iniciar la descarga. Intenta de nuevo.",
        "errors.download_failed": "La descarga ha fallado. Prueba con otra calidad o vuelve a intentarlo.",
        "errors.download_unavailable": "La descarga ya no está disponible.",
        "errors.download_not_ready": "La descarga todavía no está lista.",
        "errors.download_missing_file": "La descarga terminó sin generar archivo final.",
        "errors.extract_failed": "No se ha podido resolver la URL proporcionada.",
        "errors.invalid_format": "El formato elegido ya no es valido. Analiza la URL de nuevo.",
        "errors.no_formats": "No se han encontrado formatos descargables para esta URL.",
        "errors.ffmpeg_missing": "Falta ffmpeg en el sistema. Instala ffmpeg y anadelo al PATH para poder fusionar video y audio o convertir a MP3.",
        "errors.unsupported_url": "La URL no pertenece a una plataforma soportada por el motor de descarga.",
        "errors.private_or_login": "El contenido parece privado o requiere autenticacion.",
        "errors.youtube_bot_protection": "YouTube ha pedido autenticacion para esta descarga. OmniDown intentara usar automaticamente la sesion de un navegador local si esta instancia corre en la misma maquina. Si corre en un servidor remoto, ese servidor necesita su propia sesion autenticada.",
        "errors.unavailable_content": "El contenido no esta disponible para descarga en este momento.",
        "errors.generic_processing": "No hemos podido procesar la URL indicada.",
        "jobs.preparing": "Preparando descarga...",
        "jobs.connecting": "Conectando con la fuente...",
        "jobs.processing": "Procesando archivo final...",
        "jobs.ready": "Listo para descargar",
        "jobs.failed_retry": "La descarga ha fallado. Prueba otra calidad.",
        "jobs.speed": "{speed} MB/s",
        "jobs.eta": "ETA {seconds} s",
        "formats.video": "Video {quality} ({ext}, {suffix})",
        "formats.audio": "Audio {quality} ({ext})",
        "formats.video_with_audio": "video+audio",
        "formats.video_only_plus_audio": "solo video + audio",
    },
    "en": {
        "errors.analyze_unexpected": "We could not analyze the URL. Try again in a few seconds.",
        "errors.prepare_download_unexpected": "We could not prepare the download. Try again.",
        "errors.create_download_unexpected": "We could not start the download. Try again.",
        "errors.download_failed": "The download failed. Try another quality or try again.",
        "errors.download_unavailable": "This download is no longer available.",
        "errors.download_not_ready": "The download is not ready yet.",
        "errors.download_missing_file": "The download finished without producing a final file.",
        "errors.extract_failed": "We could not resolve the URL you provided.",
        "errors.invalid_format": "The selected format is no longer valid. Analyze the URL again.",
        "errors.no_formats": "No downloadable formats were found for this URL.",
        "errors.ffmpeg_missing": "ffmpeg is missing on this system. Install ffmpeg and add it to PATH to merge video and audio or convert to MP3.",
        "errors.unsupported_url": "The URL does not belong to a platform supported by the download engine.",
        "errors.private_or_login": "The content appears to be private or requires authentication.",
        "errors.youtube_bot_protection": "YouTube is requiring authentication for this download. OmniDown will try to use a local browser session automatically when this instance runs on the same machine. If it runs on a remote server, that server needs its own authenticated browser session.",
        "errors.unavailable_content": "This content is not available for download right now.",
        "errors.generic_processing": "We could not process the provided URL.",
        "jobs.preparing": "Preparing download...",
        "jobs.connecting": "Connecting to source...",
        "jobs.processing": "Processing final file...",
        "jobs.ready": "Ready to download",
        "jobs.failed_retry": "The download failed. Try another quality.",
        "jobs.speed": "{speed} MB/s",
        "jobs.eta": "ETA {seconds} s",
        "formats.video": "Video {quality} ({ext}, {suffix})",
        "formats.audio": "Audio {quality} ({ext})",
        "formats.video_with_audio": "video+audio",
        "formats.video_only_plus_audio": "video only + audio",
    },
}


def normalize_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    primary = value.split(",")[0].strip().split("-")[0].lower()
    return primary if primary in SUPPORTED_LOCALES else DEFAULT_LOCALE


def get_request_locale(request: Request) -> str:
    return normalize_locale(request.headers.get("accept-language"))


def t(locale: str, key: str, **kwargs: object) -> str:
    language = normalize_locale(locale)
    template = TRANSLATIONS.get(language, TRANSLATIONS[DEFAULT_LOCALE]).get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LOCALE].get(key, key)
    return template.format(**kwargs)
