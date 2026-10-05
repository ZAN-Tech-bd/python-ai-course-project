#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# MediaPipe needs Python 3.9-3.12, so prefer one of those over the default python3.
PYBIN=""
for v in 3.12 3.11 3.10 3.9; do
    if command -v "python$v" >/dev/null 2>&1; then PYBIN="python$v"; break; fi
done
[ -z "$PYBIN" ] && PYBIN="python3"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv ..."
    "$PYBIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing/updating dependencies..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo
echo "Starting Food Slice..."
python main.py "$@"
