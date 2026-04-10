#!/usr/bin/env bash
# Despliega nginx-nodeone.conf a sites-available si el archivo existe en el repo.
# Si nginx-nodeone.conf no está (vhost retirado), este script falla con mensaje claro.
set -euo pipefail

SITE_NAME="${NGINX_SITE_NAME:-apps.easynodeone.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC="${REPO_ROOT}/nginx-nodeone.conf"
AVAILABLE="/etc/nginx/sites-available/${SITE_NAME}"
ENABLED="/etc/nginx/sites-enabled/${SITE_NAME}"
BACKUP_ROOT="/var/backups/nginx-nodeone"
TS="$(date +%Y%m%d-%H%M%S)"
DRY_RUN=0

usage() {
  echo "Uso: sudo $0 [--dry-run]"
  echo "  Requiere nginx-nodeone.conf en la raíz del repo (si fue borrado, el vhost NodeOne en Nginx está retirado)."
  echo "Env: NGINX_SITE_NAME (default: apps.easynodeone.com)"
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { usage; exit 0; }
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Error: ejecutar con sudo: sudo $0 $*"
  exit 1
fi

if [[ ! -f "$SRC" ]]; then
  echo "Error: no existe $SRC — no hay conf NodeOne para desplegar (sitio easynodeone en Nginx eliminado)."
  exit 1
fi

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

BACKUP_FILE=""
run "mkdir -p \"$BACKUP_ROOT\""
if [[ -f "$AVAILABLE" ]]; then
  BACKUP_FILE="${BACKUP_ROOT}/${SITE_NAME}.conf.bak-${TS}"
  run "cp -a \"$AVAILABLE\" \"$BACKUP_FILE\""
  if [[ "$DRY_RUN" -eq 0 ]] && [[ -n "$BACKUP_FILE" ]]; then
    echo "Backup: $BACKUP_FILE"
  fi
fi

run "install -m 0644 \"$SRC\" \"$AVAILABLE\""
echo "Instalado: $AVAILABLE"

if [[ -L "$ENABLED" ]] || [[ -e "$ENABLED" ]]; then
  run "rm -f \"$ENABLED\""
fi
run "ln -sf \"$AVAILABLE\" \"$ENABLED\""
echo "Enlace: $ENABLED -> $AVAILABLE"

LEGACY_ENABLE=/etc/nginx/sites-enabled/app.easynodeone.com
if [[ -L "$LEGACY_ENABLE" ]] || [[ -e "$LEGACY_ENABLE" ]]; then
  run "rm -f \"$LEGACY_ENABLE\""
  echo "Eliminado enlace legado: $LEGACY_ENABLE"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] nginx -t && systemctl reload nginx"
  exit 0
fi

if ! nginx -t 2>&1; then
  echo "Error: nginx -t falló."
  [[ -n "$BACKUP_FILE" ]] && echo "Restaurá si aplica: cp -a \"$BACKUP_FILE\" \"$AVAILABLE\" && nginx -t && systemctl reload nginx"
  exit 1
fi

systemctl reload nginx
echo "OK: nginx recargado."
