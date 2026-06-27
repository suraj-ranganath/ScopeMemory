#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if command -v conda >/dev/null && conda info --envs 2>/dev/null | grep -q scopemem; then
  PYTHON="$(conda run -n scopemem which python 2>/dev/null || echo python3)"
fi

echo "=== 1/3 Start Dolt + Gateway (Docker) ==="
docker compose --profile gateway-docker up -d --build
"$PYTHON" run_demo.py
