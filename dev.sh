#!/usr/bin/env bash
# Lance l'API (port 8000) et le site (port 3000) en local.
# Paiements simulés par défaut (FAPSHI_MODE=mock) :
#   numéro finissant par 0 -> payé, par 1 -> échec.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d api/.venv ]; then
  python3 -m venv api/.venv
  api/.venv/bin/pip install -r api/requirements.txt
fi
if [ ! -d web/node_modules ]; then
  (cd web && npm install)
fi

set -a; [ -f api/.env ] && . api/.env; set +a

(cd api && .venv/bin/uvicorn app.main:app --reload --port 8000) &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
cd web && npm run dev
