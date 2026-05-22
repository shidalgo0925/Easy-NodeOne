#!/usr/bin/env bash
# Aplica release IIUS → develop en DEV (extrae tar, commit, tag).
# Uso: bash backend/scripts/dev_apply_iius_tarball.sh /tmp/iius-release-to-dev_YYYYMMDD_HHMM.tar.gz
set -euo pipefail

TAR="${1:?Ruta al tarball requerida}"
APP_ROOT="/opt/easynodeone/dev/app"
TAG_NAME="iius-go-20260522"

if [[ ! -f "$TAR" ]]; then
  echo "ERROR: no existe: $TAR" >&2
  exit 1
fi

cd "$APP_ROOT"
git checkout develop
git pull origin develop

echo "==> Extrayendo $TAR"
tar -xzf "$TAR" -C "$APP_ROOT"

PATHS_FILE="$APP_ROOT/backend/docs/IIUS_COMMIT_PATHS.txt"
MSG_FILE="$APP_ROOT/backend/docs/IIUS_COMMIT_MESSAGE.txt"
if [[ ! -f "$PATHS_FILE" || ! -f "$MSG_FILE" ]]; then
  echo "ERROR: faltan $PATHS_FILE o $MSG_FILE (¿tar incompleto?)" >&2
  exit 1
fi

mapfile -t ADD_PATHS < <(grep -v '^#' "$PATHS_FILE" | grep -v '^[[:space:]]*$' || true)
if [[ ${#ADD_PATHS[@]} -eq 0 ]]; then
  echo "ERROR: IIUS_COMMIT_PATHS.txt vacío" >&2
  exit 1
fi

for p in "${ADD_PATHS[@]}"; do
  if [[ "$p" == *".env"* ]]; then
    echo "ERROR: ruta prohibida en manifest: $p" >&2
    exit 1
  fi
done

git add "${ADD_PATHS[@]}"

if git diff --cached --name-only | grep -qE '(^|/)\.env$|\.env\.|/\.env'; then
  echo "ERROR: .env en staging — abortando" >&2
  git reset HEAD
  exit 1
fi

if git diff --cached --quiet; then
  echo "WARN: sin cambios tras extraer; revisar si el release ya está aplicado."
  exit 0
fi

echo "==> Cambios a commitear:"
git diff --cached --stat

git commit -F "$MSG_FILE"

if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
  git tag -f -a "$TAG_NAME" -m "Release IIUS operativo mayo 2026"
else
  git tag -a "$TAG_NAME" -m "Release IIUS operativo mayo 2026"
fi

echo "==> OK. Siguiente:"
echo "  git push origin develop"
echo "  git push origin $TAG_NAME"
echo "  # si el tag existía remoto: git push origin $TAG_NAME --force"
