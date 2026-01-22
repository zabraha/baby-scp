#!/bin/sh
while [ $# -gt 0 ]; do
  case $1 in
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --card-url) export CARD_URL="$2"; shift 2 ;;
    *) break ;;
  esac
done
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-9009}"
exec python -m uvicorn purple-agent.main:app --host "$HOST" --port "$PORT" "$@"
