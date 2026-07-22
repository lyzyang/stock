#!/bin/bash

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_SCRIPT="$BASE_DIR/src/main.py"

if [ -f "$BASE_DIR/venv/bin/python" ]; then
    PYTHON="$BASE_DIR/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "Error: Python not found" >&2
    exit 1
fi

HOUR=$(date +%-H)
MINUTE=$(date +%-M)
CURRENT_MINUTES=$((HOUR * 60 + MINUTE))
LUNCH_START=$((11 * 60 + 30))
LUNCH_END=$((12 * 60 + 55))

if [ $CURRENT_MINUTES -ge $LUNCH_START ] && [ $CURRENT_MINUTES -lt $LUNCH_END ]; then
    exit 0
fi

"$PYTHON" "$PYTHON_SCRIPT"