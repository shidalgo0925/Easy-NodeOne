#!/usr/bin/env bash
# Despliega nginx-nodeone-app1.conf (Easy NodeOne en app1.easynodeone.com). Requiere sudo.
set -euo pipefail

SITE_NAME="${NGINX_APP1_SITE_NAME:-app1.easynodeone.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC="${REPO_ROOT}/nginx-nodeone-app1.conf"
AVAILABLE="/etc/nginx/sites-available/${SITE_NAME}"
ENABLED="/etc/nginx/sites-enabled/${SITE_NAME}"
BACKUP_ROOT="/var/backups/nginx-nodeone-app1"
TS="$(date +%Y%m%d_%H%M%S)"
DRY_RUN=0

usage() {
  echo "Uso: sudo $0 [--dry-run]"
  echo "  En el servidor donde A app1 → esta IP (ej. 86.48.20.243)."
  echo "Env: NGINX_APP1_SITE_NAME (default: app1.easynodeone.com)"
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { usage; exit 0; }
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Error: ejecutar con sudo: sudo $0 $*"
  exit 1
fi

if [[ ! -f "$SRC" ]]; then
  echo "Error: no existe fuente: $SRC"
  exit 1
fi

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

run "mkdir -p \"$BACKUP_ROOT\""
BACKUP_FILE=""
if [[ -f "$AVAILABLE" ]]; then
  BACKUP_FILE="${BACKUP_ROOT}/${SITE_NAME}.conf.bak-${TS}"
  run "cp -a \"$AVAILABLE\" \"$BACKUP_FILE\""
  [[ "$DRY_RUN" -eq 0 ]] && [[ -n "$BACKUP_FILE" ]] && echo "Backup: $BACKUP_FILE"
fi

run "install -m 0644 \"$SRC\" \"$AVAILABLE\""
echo "Instalado: $AVAILABLE"
run "rm -f \"$ENABLED\""
run "ln -sf \"$AVAILABLE\" \"$ENABLED\""
echo "Enlace: $ENABLED -> $AVAILABLE"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] nginx -t && systemctl reload nginx"
  exit 0
fi

if ! nginx -t 2>&1; then
  echo "Error: nginx -t falló."
  [[ -n "$BACKUP_FILE" ]] && echo "Restaurá: cp -a \"$BACKUP_FILE\" \"$AVAILABLE\" && nginx -t && systemctl reload nginx"
  exit 1
fi

systemctl reload nginx
echo "OK: nginx recargado (app1.easynodeone.com → 127.0.0.1:8000)."
