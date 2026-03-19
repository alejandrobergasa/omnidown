#!/usr/bin/env sh
set -eu

nginx
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 600 \
  --access-logfile - \
  --error-logfile -
