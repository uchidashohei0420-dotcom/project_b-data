#!/usr/bin/env bash
# Thin wrapper the GitHub Actions workflow (and local manual runs) invoke.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m collector.main
