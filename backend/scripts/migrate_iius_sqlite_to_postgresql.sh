#!/usr/bin/env bash
# Migra NodeOne.db (SQLite) → PostgreSQL IIUS.
# Requiere: postgresql, pgloader, sqlite3.
#
# Uso:
#   ./scripts/migrate_iius_sqlite_to_postgresql.sh              # dry-run (solo muestra pasos)
#   ./scripts/migrate_iius_sqlite_to_postgresql.sh --apply
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND="$(cd "$(dirname "$0")/.." && pwd)"
SQLITE="${SQLITE_PATH:-$ROOT/instance/NodeOne.db}"
APPLY=false
[[ "${1:-}" == "--apply" ]] && APPLY=true

if [[ ! -f "$SQLITE" ]]; then
  echo "No existe SQLite: $SQLITE" >&2
  exit 1
fi

echo "SQLite: $SQLITE ($(du -h "$SQLITE" | cut -f1))"
echo "Modo: $( $APPLY && echo APPLY || echo DRY-RUN )"

if ! $APPLY; then
  echo "Con --apply:"
  echo "  1. Backup SQLite en backups/"
  echo "  2. Crear rol/BD iius_nodeone (si no existe)"
  echo "  3. pgloader → postgresql://iius_nodeone_app@127.0.0.1:5432/iius_nodeone"
  echo "  4. Añadir DATABASE_URL al .env"
  echo "  5. bootstrap_nodeone_schema + systemctl restart nodeone"
  exit 0
fi

STAMP=$(date +%Y%m%d_%H%M%S)
cp -a "$SQLITE" "$ROOT/backups/NodeOne_pre_postgres_${STAMP}.db"
echo "Backup: backups/NodeOne_pre_postgres_${STAMP}.db"

PW_FILE="$ROOT/instance/.pg_password"
if [[ ! -f "$PW_FILE" ]]; then
  python3 -c "import secrets; print(secrets.token_urlsafe(24))" > "$PW_FILE"
  chmod 600 "$PW_FILE"
fi
PG_PASS=$(cat "$PW_FILE")
export PGPASSWORD="$PG_PASS"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<'EOSQL' || true
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'iius_nodeone_app') THEN
    CREATE ROLE iius_nodeone_app LOGIN;
  END IF;
END $$;
EOSQL
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER ROLE iius_nodeone_app PASSWORD '$PG_PASS';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='iius_nodeone'" | grep -q 1 \
  || sudo -u postgres createdb -O iius_nodeone_app iius_nodeone
sudo -u postgres psql -d iius_nodeone -c "GRANT ALL ON SCHEMA public TO iius_nodeone_app;"

PG_URL="postgresql://iius_nodeone_app:${PG_PASS}@127.0.0.1:5432/iius_nodeone"
pgloader "$SQLITE" "$PG_URL"

cd "$BACKEND"
source "$ROOT/.venv/bin/activate"
export DATABASE_URL="$PG_URL"
export SQLALCHEMY_DATABASE_URI="$PG_URL"
python -c "from app import bootstrap_nodeone_schema; bootstrap_nodeone_schema()"

ENV_FILE="$ROOT/.env"
if ! grep -q '^DATABASE_URL=' "$ENV_FILE" 2>/dev/null; then
  printf '\n# PostgreSQL IIUS (migrado %s)\nDATABASE_URL=%s\nSQLALCHEMY_DATABASE_URI=%s\n' \
    "$(date +%Y-%m-%d)" "$PG_URL" "$PG_URL" >> "$ENV_FILE"
fi

echo "Listo. Reiniciar: sudo systemctl restart nodeone.service"
echo "Verificar: cd backend && python scripts/audit_iius_infra_readiness.py"
