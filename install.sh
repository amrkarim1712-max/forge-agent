#!/usr/bin/env sh
set -eu

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python 3.11+ is required. Install it and rerun this script." >&2
  exit 1
fi

version="$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
case "$version" in
  3.11|3.12|3.13|3.14) ;;
  *) echo "Forge Agent needs Python 3.11+; found $version." >&2; exit 1 ;;
esac

if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
forge --version

cat <<'NEXT'

Forge Agent is installed in the local virtual environment.
Set OPENAI_API_KEY or configure Groq with FORGE_PROVIDER=groq and GROQ_API_KEY, then run:
  source .venv/bin/activate
  forge doctor
  forge
NEXT