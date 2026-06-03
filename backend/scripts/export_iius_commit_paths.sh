#!/usr/bin/env bash
# Lista rutas para copiar/commit en dev/app (desde raíz del silo /opt/easynodeone/app).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
echo "# IIUS release paths — $(date -u +%Y-%m-%dT%H:%MZ)"
git status --porcelain | awk '{print $2}'
