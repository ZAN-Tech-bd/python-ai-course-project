#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PYBIN="python3"
command -v python3 >/dev/null 2>&1 || PYBIN="python"

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
echo "Starting Draw in Air..."
python main.py
