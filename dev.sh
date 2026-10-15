#!/usr/bin/env bash
# ClimaSense — sobe a API (porta 8000) e o frontend (porta 5173) para desenvolvimento.
# Primeira vez:
#   python3.12 -m venv .venv && .venv/bin/pip install -e "./backend[dev]"
#   (cd frontend && npm install) && cp .env.example .env   # e preencha
set -euo pipefail
raiz="$(cd "$(dirname "$0")" && pwd)"
"$raiz/.venv/bin/python" -m uvicorn climasense.api.main:app --reload --port 8000 --app-dir "$raiz/backend" &
api=$!
trap 'kill $api 2>/dev/null' EXIT
cd "$raiz/frontend" && npm run dev
