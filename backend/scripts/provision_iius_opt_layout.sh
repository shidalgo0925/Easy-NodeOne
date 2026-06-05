#!/usr/bin/env bash
# Crea esqueleto /opt/iius/{dev,staging,prod} (sin mover runtime actual).
set -euo pipefail
BASE="${IIUS_OPT_ROOT:-/opt/iius}"

sudo mkdir -p "$BASE"/{dev,staging,prod}/{app,backups,logs}
sudo chown -R adminnode:www-data "$BASE"
sudo chmod 775 "$BASE" "$BASE"/* 

for env in dev staging prod; do
  cat > "/tmp/iius-env-example-${env}.txt" <<EOF
# Plantilla $env — copiar a $BASE/$env/app/.env (no versionar secretos)
DATABASE_URL=postgresql://USER:PASS@127.0.0.1:5432/iius_nodeone_${env}
NODEONE_BRAND_PRESET=iius
REQUIRE_PAID_ACCESS=true
BASE_URL=https://apps.internationalinstitute.us
DEFAULT_ORGANIZATION_ID=1
EOF
  sudo cp "/tmp/iius-env-example-${env}.txt" "$BASE/$env/.env.example"
done

sudo tee "$BASE/README.md" >/dev/null <<'EOF'
# IIUS — layout de entornos

| Silo | Uso actual | Ruta |
|------|------------|------|
| **prod (activo)** | Runtime IIUS en este host | `/opt/easynodeone/app` |
| dev | Sandbox futuro | `/opt/iius/dev/app` |
| staging | Pre-prod futuro | `/opt/iius/staging/app` |
| prod (futuro) | Espejo formal cuando se separe | `/opt/iius/prod/app` |

Hoy **producción** sigue en `/opt/easynodeone` (rama `iius-product`, systemd `nodeone.service`).

PostgreSQL IIUS prod: base `iius_nodeone` en `127.0.0.1:5432`.

No editar `/var/www/nodeone` para deploy IIUS.
EOF

sudo tee "$BASE/prod/README.md" >/dev/null <<'EOF'
Producción IIUS operativa: `/opt/easynodeone/app` (no mover sin ventana de mantenimiento).
EOF

echo "Creado $BASE (dev, staging, prod skeleton)"
