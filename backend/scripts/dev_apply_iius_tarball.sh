#!/usr/bin/env bash
# Ejecutar EN DEV (/opt/easynodeone/dev/app) tras scp del tarball a /tmp.
set -euo pipefail

TAR="${1:-/tmp/iius-release-to-dev_20260522_2249.tar.gz}"
APP_ROOT="${IIUS_DEV_APP_ROOT:-/opt/easynodeone/dev/app}"

if [[ ! -f "$TAR" ]]; then
  echo "FAIL: no existe $TAR"
  exit 1
fi
if [[ ! -d "$APP_ROOT/.git" ]]; then
  echo "FAIL: $APP_ROOT no es repo git"
  exit 1
fi

cd "$APP_ROOT"
git checkout develop
git pull origin develop

tar -xzf "$TAR"
echo "--- git status (primeras 30 líneas) ---"
git status -sb | head -30

if git status --porcelain | grep -qE '^.. \.env$|^.. backend/\.env$'; then
  echo "FAIL: .env en staging — no commitear secretos"
  exit 1
fi

PATHS_FILE=backend/docs/IIUS_COMMIT_PATHS.txt
if [[ ! -f "$PATHS_FILE" ]]; then
  echo "FAIL: falta $PATHS_FILE tras extraer tar"
  exit 1
fi

git add $(grep -v '^#' "$PATHS_FILE" | grep -v '^$' | while read -r p; do [[ -e "$p" ]] && echo "$p"; done)

git commit -F backend/docs/IIUS_COMMIT_MESSAGE.txt

if git rev-parse iius-go-20260522 >/dev/null 2>&1; then
  echo "WARN: tag iius-go-20260522 ya existe; no se recrea"
else
  git tag -a iius-go-20260522 -m "Release IIUS operativo mayo 2026"
fi

echo "OK commit $(git log -1 --oneline)"
echo "Siguiente: git push origin develop && git push origin iius-go-20260522"
