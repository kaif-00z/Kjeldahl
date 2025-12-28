#!/bin/sh

# load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# runner
gunicorn main:app -k uvicorn.workers.UvicornWorker \
    --bind ${HOST:-0.0.0.0}:${PORT:-5000} \
    --preload \
    --max-requests ${MAX_REQ_BUFFER:-10000} \
    --max-requests-jitter $(( ${MAX_REQ_BUFFER:-10000} / 10 )) \
    --workers $(( $(nproc) * 2 + 1 ))