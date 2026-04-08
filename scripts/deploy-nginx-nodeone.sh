#!/usr/bin/env bash
# Despliega nginx-nodeone.conf a sites-available, enlace en sites-enabled,
# backup del anterior, nginx -t y reload. Requiere root o sudo.
set -euo pipefail

# Mismo nombre que en producción: sites-available/app.easynodeone.com
SITE_NAME="${NGINX_SITE_NAME:-app.easynodeone.com}"
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
  echo "  --dry-run  Solo muestra acciones, no escribe ni recarga."
  echo "Env: NGINX_SITE_NAME (default: app.easynodeone.com)"
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
