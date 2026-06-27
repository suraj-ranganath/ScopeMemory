#!/usr/bin/env bash
# Launch Streamlit Policy Console (gateway must be running on :8080)
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
exec streamlit run streamlit_app.py --server.headless true
