#!/usr/bin/env bash
# Limpieza post-deploy: archivos legacy, cachés Python y (opcional) untracked seguro.
#
# Uso:
#   bash scripts/post_deploy_cleanup.sh <dev|staging|prod|relatic|iius|all> [--dry-run] [--git-clean]
#
# Ejecutar DESPUÉS de git pull / checkout del tag acordado y ANTES del restart
# (o justo después del restart; no afecta BD ni uploads de usuario).
#
# Integración con deploy del servidor:
#   bash "${APP}/scripts/post_deploy_cleanup.sh" staging
#   (añadir en /opt/easynodeone/scripts/deploy-easynodeone-instance.sh tras el pull)
#
# IIUS (host dedicado): árbol en /opt/easynodeone/app — misma repo, preset de marca IIUS.
#
# PROD: requiere EASYNODEONE_DEPLOY_PROD_CONFIRM=YES (misma norma que deploy-easynodeone-instance.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST="${SCRIPT_DIR}/deploy_cleanup_manifest.txt"

DRY_RUN=0
GIT_CLEAN=0
INSTANCES=()

usage() {
  cat <<'EOF'
Uso: post_deploy_cleanup.sh <instancia> [opciones]

Instancias:
  dev | staging | prod | relatic | iius | all
  (all = dev + staging + relatic; prod solo con confirmación)

Opciones:
  --dry-run     Muestra qué haría sin borrar
  --git-clean   Además: git clean -fd con exclusiones (uploads, .env, instance, venv)
  -h, --help    Esta ayuda

Ejemplos:
  bash scripts/post_deploy_cleanup.sh staging
  bash scripts/post_deploy_cleanup.sh prod --dry-run
  bash scripts/post_deploy_cleanup.sh all --git-clean
EOF
}

log() { printf '%s\n' "$*"; }
run_rm() {
  local target="$1"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "[dry-run] rm -rf -- $target"
  else
    rm -rf -- "$target"
    log "removed: $target"
  fi
}

resolve_app_dir() {
  local inst="$1"
  case "$inst" in
    dev|staging|prod|relatic)
      echo "/opt/easynodeone/${inst}/app"
      ;;
    iius)
      echo "/opt/easynodeone/app"
      ;;
    *)
      echo "ERROR: instancia desconocida: $inst" >&2
      return 1
      ;;
  esac
}

clean_manifest_paths() {
  local app="$1"
  [[ -f "$MANIFEST" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [[ -z "$line" ]] && continue
    if [[ "$line" == *'*'* || "$line" == *'?'* ]]; then
      while IFS= read -r -d '' target; do
        [[ "$target" == "$app/static/uploads"* ]] && continue
        run_rm "$target"
      done < <(find "$app" -name "$(basename "$line")" -not -path '*/static/uploads/*' -print0 2>/dev/null || true)
    elif [[ -e "$app/$line" ]]; then
      [[ "$app/$line" == "$app/static/uploads"* ]] && { log "skip (uploads): $app/$line"; continue; }
      run_rm "$app/$line"
    fi
  done < "$MANIFEST"
}

clean_python_caches() {
  local app="$1"
  local -a search_dirs=()
  for d in backend templates scripts config landing md docs static; do
    [[ -d "$app/$d" ]] && search_dirs+=("$app/$d")
  done
  [[ ${#search_dirs[@]} -eq 0 ]] && return 0
  while IFS= read -r -d '' target; do
    run_rm "$target"
  done < <(
    find "${search_dirs[@]}" \
      \( -path "$app/static/uploads" -o -path "$app/static/uploads/*" \) -prune \
      -o \( -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' \) \
        -o -type f \( -name '*.pyc' -o -name '*.pyo' \) \) -print0 2>/dev/null || true
  )
}

clean_git_untracked() {
  local app="$1"
  [[ -d "$app/.git" ]] || { log "skip git-clean: no .git en $app"; return 0; }
  local -a excludes=(
    -e 'static/uploads/'
    -e 'static/public/emails/logos/'
    -e 'instance/'
    -e 'backups/'
    -e '.env'
    -e '.env.*'
    -e 'venv/'
    -e '.venv/'
    -e 'logs/'
    -e '*.log'
    -e 'cookies.txt'
  )
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "[dry-run] git -C $app clean -fdn ${excludes[*]}"
    git -C "$app" clean -fdn "${excludes[@]}" || true
  else
    log "git clean -fd (con exclusiones de uploads/.env/instance)"
    git -C "$app" clean -fd "${excludes[@]}"
  fi
}

clean_instance() {
  local inst="$1"
  local app
  app="$(resolve_app_dir "$inst")"

  if [[ ! -d "$app" ]]; then
    log "==> [$inst] SKIP: no existe $app"
    return 0
  fi

  if [[ "$inst" == "prod" && "$DRY_RUN" -eq 0 && "${EASYNODEONE_DEPLOY_PROD_CONFIRM:-}" != "YES" ]]; then
    log "ERROR: prod requiere EASYNODEONE_DEPLOY_PROD_CONFIRM=YES"
    exit 1
  fi

  log "==> [$inst] limpieza en $app"

  # Manifiesto versionado (viaja con el repo; puede diferir si el silo no hizo pull aún)
  local manifest="$app/scripts/deploy_cleanup_manifest.txt"
  if [[ -f "$manifest" ]]; then
    MANIFEST="$manifest"
  fi

  clean_manifest_paths "$app"
  clean_python_caches "$app"

  if [[ "$GIT_CLEAN" -eq 1 ]]; then
    clean_git_untracked "$app"
  fi

  log "==> [$inst] OK"
}

# --- args ---
if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --git-clean) GIT_CLEAN=1; shift ;;
    dev|staging|prod|relatic|iius)
      INSTANCES+=("$1")
      shift
      ;;
    all)
      INSTANCES+=(dev staging relatic)
      if [[ "${EASYNODEONE_DEPLOY_PROD_CONFIRM:-}" == "YES" ]]; then
        INSTANCES+=(prod)
      else
        log "NOTA: 'all' omite prod (exporta EASYNODEONE_DEPLOY_PROD_CONFIRM=YES para incluirlo)"
      fi
      # IIUS solo si existe el árbol
      if [[ -d /opt/easynodeone/app ]]; then
        INSTANCES+=(iius)
      fi
      shift
      ;;
    *)
      echo "ERROR: argumento desconocido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ${#INSTANCES[@]} -eq 0 ]]; then
  usage
  exit 1
fi

for inst in "${INSTANCES[@]}"; do
  clean_instance "$inst"
done

log "==> Limpieza post-deploy completada"
