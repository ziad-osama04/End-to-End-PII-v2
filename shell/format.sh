#!/usr/bin/env bash
# Apply import sorting, lint fixes, and formatting in place.
set -euo pipefail
cd "$(dirname "$0")/.."

ruff check --fix .
black .
