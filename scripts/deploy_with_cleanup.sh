#!/usr/bin/env bash
# Deploy EN1 + limpieza post-pull (referencia para operación en el servidor).
# Copiar o enlazar desde /opt/easynodeone/scripts/ si el equipo lo prefiere centralizado.
#
# Uso:
#   sudo bash scripts/deploy_with_cleanup.sh <dev|staging|prod|relatic> [rama]
#   sudo EASYNODEONE_DEPLOY_PROD_CONFIRM=YES bash scripts/deploy_with_cleanup.sh prod
#
# IIUS (host dedicado, tras git pull en /opt/easynodeone/app):
#   bash /opt/easynodeone/app/scripts/post_deploy_cleanup.sh iius
#   sudo systemctl restart nodeone.service
set -euo pipefail

INST="${1:?Uso: $0 dev|staging|prod|relatic [rama]}"
BRANCH="${2:-}"

SERVER_DEPLOY="/opt/easynodeone/scripts/deploy-easynodeone-instance.sh"
APP="/opt/easynodeone/${INST}/app"

if [[ -x "$SERVER_DEPLOY" ]]; then
  if [[ -n "$BRANCH" ]]; then
    sudo bash "$SERVER_DEPLOY" "$INST" "$BRANCH"
  else
    sudo bash "$SERVER_DEPLOY" "$INST"
  fi
else
  echo "WARN: no existe $SERVER_DEPLOY; asumiendo git pull manual"
  ROOT="/opt/easynodeone/${INST}"
  case "$INST" in
    dev) DEFAULT_BRANCH=develop ;;
    *) DEFAULT_BRANCH=main ;;
  esac
  BR="${BRANCH:-$DEFAULT_BRANCH}"
  sudo -u nodeone env HOME="$ROOT" git -C "$APP" fetch origin
  sudo -u nodeone env HOME="$ROOT" git -C "$APP" checkout "$BR"
  sudo -u nodeone env HOME="$ROOT" git -C "$APP" pull origin "$BR"
fi

CLEAN="${APP}/scripts/post_deploy_cleanup.sh"
[[ -x "$CLEAN" ]] || chmod +x "$CLEAN" 2>/dev/null || true
CLEAN_ARGS=("$INST")
if [[ "${EASYNODEONE_CLEANUP_GIT:-}" == "1" || "${EASYNODEONE_CLEANUP_GIT:-}" == "YES" ]]; then
  CLEAN_ARGS+=(--git-clean)
fi
bash "$CLEAN" "${CLEAN_ARGS[@]}"

echo "==> Deploy + limpieza [$INST] listo"
