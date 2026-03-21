# OmniDown

MVP de una aplicación web pública para descargar vídeo y audio desde plataformas compatibles con `yt-dlp`, priorizando simplicidad, despliegue rápido y evolución sencilla.

## Requisitos locales en Windows

- Python 3.11 o 3.12
- `ffmpeg` instalado y disponible en `PATH`

Instalación rápida de `ffmpeg` con `winget`:

```powershell
winget install Gyan.FFmpeg
```

Verificación:

```powershell
ffmpeg -version
ffprobe -version
```

## Stack elegido

- `FastAPI` para backend y render de la página inicial.
- `Jinja2 + HTML/CSS/JS` para un frontend ligero, rápido y fácil de monetizar con Google Ads.
- `yt-dlp` como motor de extracción y descarga.
- `nginx + gunicorn/uvicorn` dentro de Docker para servir en una sola instancia.
- `ffmpeg` para conversión de audio a MP3, M4A o WAV.

## Por qué FastAPI y no Flask

- Tiene validación de datos y tipado moderno sin añadir librerías extra.
- Facilita mantener endpoints claros para `extract` y `download`.
- Escala mejor a futuro si añadimos jobs asíncronos, rate limiting o panel admin.
- Sigue siendo muy rápido de desarrollar para un MVP.

Flask también serviría, pero aquí FastAPI da mejor base de producción sin complicar el código.

## Arquitectura MVP

1. El usuario pega una URL en `/`.
2. El frontend llama a `POST /api/extract`.
3. El backend usa `yt-dlp` para detectar plataforma, título, miniatura y formatos.
4. El usuario elige una opción y dispara `GET /api/download`.
5. El backend descarga a un directorio temporal, devuelve el archivo y limpia después.

### Cola de trabajos

Para el MVP no merece la pena meter Redis o Celery:

- añade complejidad operativa,
- retrasa el desarrollo,
- y en una sola instancia con tráfico moderado las descargas síncronas son suficientes.

Sí merece la pena añadir cola cuando tengas muchas descargas simultáneas, histórico de jobs, reintentos o necesites aislar mejor CPU y red.

## Estructura del proyecto

```text
omnidown/
├── app/
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── deploy/
├── scripts/
├── .env.example
├── Dockerfile
├── README.md
└── requirements.txt
```

## Desarrollo local

### Sin Docker

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Abre `http://127.0.0.1:8000`.

Si YouTube devuelve `Sign in to confirm you're not a bot`, OmniDown intentara primero reutilizar automaticamente las cookies de un navegador local compatible (`chrome`, `edge`, `firefox`, `brave`) cuando la app corra en la misma maquina que ese navegador.

Si quieres fijar el origen de cookies de forma explicita, configura una de estas opciones en `.env` antes de arrancar la app:

```powershell
YT_DLP_COOKIES_FROM_BROWSER=chrome
YT_DLP_COOKIES_BROWSER_PROFILE=Default
```

o bien:

```powershell
YT_DLP_COOKIES_FILE=C:\ruta\cookies.txt
```

`YT_DLP_COOKIES_FROM_BROWSER` solo sirve cuando la app corre en la misma maquina que el navegador. En Docker, lo normal es montar un archivo de cookies exportado y usar `YT_DLP_COOKIES_FILE`.

Tambien puedes ajustar el comportamiento automatico:

```powershell
YT_DLP_AUTO_COOKIES_FROM_BROWSER=true
YT_DLP_BROWSER_CANDIDATES=chrome,edge,firefox,brave
YT_DLP_YOUTUBE_PLAYER_CLIENTS=
```

### Con Docker

```bash
docker build -t omnidown .
docker run --rm -p 8080:80 --env-file .env omnidown
```

Abre `http://localhost:8080`.

## Despliegue paso a paso en OCI o AWS EC2

1. Crea una instancia Ubuntu 22.04 o similar.
2. Abre en el firewall o security group los puertos `80` y `443`.
3. Instala Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

4. Sube el proyecto a la instancia.
5. Crea el archivo `.env` a partir de `.env.example`.
6. Construye la imagen:

```bash
docker build -t omnidown:latest .
```

7. Ejecuta el contenedor:

```bash
docker run -d \
  --name omnidown \
  --restart unless-stopped \
  -p 80:80 \
  --env-file .env \
  omnidown:latest
```

8. Verifica salud:

```bash
curl http://IP_PUBLICA/health
```

## Google Ads

La plantilla HTML ya incluye slots visibles para anuncios en la cabecera visual y la columna lateral. Cuando monetices, sustituye esos bloques por snippets reales de AdSense.

## Endpoints

- `GET /`
- `POST /api/extract`
- `GET /api/download`
- `GET /health`

## Mejoras futuras

- Cola con Redis + RQ o Celery.
- Rate limiting por IP.
- Caché de metadatos.
- Persistencia de analíticas.
- TLS con Caddy o nginx + Certbot.
- S3 u Object Storage para archivos grandes.
- Panel admin y métricas.

## Importante

Antes de publicar esta app conviene revisar legalidad, copyright, términos de uso de plataformas y políticas de Google Ads para este tipo de servicio.
