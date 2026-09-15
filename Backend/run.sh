#!/bin/bash

set -e

echo "Container Started"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [ -f "$HOME/.bashrc" ]; then
  # Load shell customizations when available, but do not require them.
  source "$HOME/.bashrc"
fi

cd "$SCRIPT_DIR"

# Default to auto-reload in local dev so Python edits restart the backend.
export RELOAD="${RELOAD:-true}"

if [ -x "$VENV_PYTHON" ]; then
  "$VENV_PYTHON" main.py
else
  python main.py
fi
