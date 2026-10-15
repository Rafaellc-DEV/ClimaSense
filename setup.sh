#!/usr/bin/env bash
# ClimaSense — prepara o ambiente no Linux/macOS: cria .venv, instala tudo e prepara o .env.
set -euo pipefail
cd "$(dirname "$0")"
PY=$(command -v python3.13 || command -v python3.12 || command -v python3)
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/pip install -e backend --no-deps
(cd frontend && npm ci)
if [ ! -f .env ]; then
  cp .env.example .env
  segredo=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))")
  sed -i.bak "s/^SESSION_SECRET=$/SESSION_SECRET=$segredo/" .env && rm -f .env.bak
  echo ".env criado. Preencha MONGO_URI e DATABASE_URL."
fi
.venv/bin/pre-commit install
echo "Pronto."
