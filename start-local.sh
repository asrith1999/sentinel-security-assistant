#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -f backend/.env ] || [ ! -x backend/.venv/bin/python ] || [ ! -d frontend/node_modules ]; then
  echo 'Complete README.md setup first.'
  exit 1
fi
(cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM
cd frontend
npm run dev
