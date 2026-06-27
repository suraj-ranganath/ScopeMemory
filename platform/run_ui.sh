#!/usr/bin/env bash
# Launch React UI (gateway must be running on :8080)
set -euo pipefail
cd "$(dirname "$0")"
cd web
if [ ! -d node_modules ]; then
  npm install
fi
exec npm run dev
