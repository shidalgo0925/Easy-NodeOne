#!/usr/bin/env bash
# Crea tarball con solo rutas del release IIUS (para copiar a dev/app).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="/opt/easynodeone/backups/iius-release-to-dev_${STAMP}.tar.gz"
LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT

git status --porcelain | awk '{print $2}' >"$LIST"
# Incluir lista de paths aunque no esté en git status aún
if [[ -f backend/docs/IIUS_COMMIT_PATHS.txt ]]; then
  grep -v '^#' backend/docs/IIUS_COMMIT_PATHS.txt | grep -v '^$' >>"$LIST" || true
fi
sort -u "$LIST" -o "$LIST"
# Excluir secretos
grep -vE '^\.env$|^backend/\.env$' "$LIST" >"${LIST}.safe" || true
mv "${LIST}.safe" "$LIST"

COUNT=$(wc -l <"$LIST")
if [[ "$COUNT" -lt 1 ]]; then
  echo "FAIL: sin archivos en lista"
  exit 1
fi

tar -czf "$OUT" -T "$LIST" 2>/dev/null || {
  echo "WARN: algunos paths faltan; empaquetando los existentes..."
  : >"${LIST}.ok"
  while IFS= read -r p; do
    [[ -e "$p" ]] && echo "$p" >>"${LIST}.ok"
  done <"$LIST"
  tar -czf "$OUT" -T "${LIST}.ok"
}

echo "OK: $OUT ($(du -h "$OUT" | awk '{print $1}')) — $COUNT rutas listadas"
echo "En DEV: cd /opt/easynodeone/dev/app && tar -xzf $OUT"
