#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

echo "=== 1/3 Init Dolt remote user (once) ==="
"$PYTHON" init_dolt_user.py 2>/dev/null || true

echo "=== 2/3 Start Dolt + Gateway (Docker) ==="
docker compose --profile gateway-docker up -d --build

echo "=== 3/3 Run demo (waits for gateway) ==="
sleep 5
"$PYTHON" run_demo.py
