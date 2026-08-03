#!/usr/bin/env bash
# Check formatting and lint rules without changing files. CI runs this exact
# script, so local and CI checks cannot drift apart.
set -euo pipefail
cd "$(dirname "$0")/.."

ruff check .
black --check .
