#!/usr/bin/env bash
# run_dev.sh — one-shot macOS dev environment setup for TV Distance Monitor
set -euo pipefail

PYTHON="${PYTHON:-python3.11}"
VENV_DIR="venv"

echo "==> Checking Python..."
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: $PYTHON not found."
    echo "Install it with: brew install python@3.11"
    exit 1
fi

PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PY_VER" != "3.11" ]]; then
    echo "WARNING: Expected Python 3.11, found $PY_VER. Behaviour may differ from CI."
fi

echo "==> Creating virtualenv in $VENV_DIR (if absent)..."
if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON" -m venv "$VENV_DIR"
fi

echo "==> Activating virtualenv..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "==> Verifying imports..."

check_import() {
    local module="$1"
    local hint="$2"
    if ! python -c "import $module" 2>/dev/null; then
        echo "  FAIL: '$module' could not be imported."
        if [[ -n "$hint" ]]; then
            echo "  Hint: $hint"
        fi
        return 1
    fi
    echo "  OK:   $module"
}

FAILED=0

check_import cv2       "" || FAILED=1
check_import numpy     "" || FAILED=1
check_import pyttsx3   "" || FAILED=1
check_import pystray   "" || FAILED=1
check_import PIL       "" || FAILED=1
check_import tkinter   "brew install python-tk@3.11  (then recreate the venv)" || FAILED=1

if [[ "$FAILED" -eq 1 ]]; then
    echo ""
    echo "One or more imports failed. Fix the hints above and re-run this script."
    exit 1
fi

echo ""
echo "==> Running unit tests..."
pytest tests/unit/ -q

echo ""
echo "Setup complete."
echo "To launch the app:         python main.py"
echo "To launch with one camera: python main.py --one-camera"
echo "To deactivate the venv:    deactivate"
