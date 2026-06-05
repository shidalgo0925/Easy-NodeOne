# IIUS — preparación infraestructura

Estado en host `vmi3215083` (2026-05-27). La línea viva sigue siendo **`iius-product`** en `/opt/easynodeone/app`.

## Hoy (silo único)

| Componente | Ruta / valor |
|------------|----------------|
| Código + Git | `/opt/easynodeone/app` → rama `iius-product` |
| Runtime | `nodeone.service` → `WorkingDirectory=/opt/easynodeone/app/backend` |
| Config | `/opt/easynodeone/app/.env` |
| BD | **PostgreSQL 16** `iius_nodeone` @ `127.0.0.1:5432` (migrado desde SQLite 2026-05-27) |
| Backup pre-Postgres | `/opt/easynodeone/backups/NodeOne_pre_postgres_*.db` |
| Credenciales PG | `/opt/easynodeone/app/instance/.pg_password` (no commitear) |
| Uploads | `static/uploads/` |
| Backups freeze | `/opt/easynodeone/backups/iius-freeze-20260527_*` |

**No usar como runtime IIUS:** `/var/www/nodeone` (otro despliegue histórico).

## Silos `/opt/iius` (esqueleto 2026-05-27)

Creado con `backend/scripts/provision_iius_opt_layout.sh`. **Prod real sigue en** `/opt/easynodeone/app`.

```
/opt/iius/
  README.md
  dev/{app,backups,logs}/      → .env.example
  staging/{app,backups,logs}/
  prod/{app,backups,logs}/
```

Cada silo futuro: clonar repo, `.env`, venv, systemd unit, dominio propio.

## Checklist antes de separar entornos

1. **Git limpio** en `iius-product` (sin detached HEAD ni WIP sin commit).
2. **Tags de hito** publicados (`iius-resources-v1`, `iius-lead-capture-v1`, …).
3. **Smokes en prod** (ejecutar desde `backend/`):
   - `python scripts/smoke_iius_catalog_events.py`
   - `python scripts/smoke_iius_payments_ops.py`
   - `python scripts/test_academic_gate_iius.py`
   - Matriz acceso real (10 casos) documentada en chat/ops.
4. **Backup** `.env` + `instance/` + `static/uploads/` antes de cualquier migración.
5. **Postgres (hecho en prod):** `migrate_iius_sqlite_to_postgresql.sh` + `bootstrap_nodeone_schema()`; verificar con `audit_iius_infra_readiness.py` (`engine: …/iius_nodeone`).

## Auditoría repetible

```bash
cd /opt/easynodeone/app/backend
source ../.venv/bin/activate
python scripts/audit_iius_infra_readiness.py
python scripts/audit_iius_catalog_events.py
python scripts/audit_iius_payments_ops.py
```

## Operación pagos — limpieza test

Cancelar Yappy manual de prueba (≤ $1, sin comprobante):

```bash
python scripts/ops_cancel_iius_yappy_test_payment.py          # dry-run
python scripts/ops_cancel_iius_yappy_test_payment.py --apply  # ejecutar
```

## Migración SQLite → Postgres (referencia)

```bash
# Requiere: postgresql, pgloader, backup previo
sudo bash backend/scripts/migrate_iius_sqlite_to_postgresql.sh
systemctl restart nodeone.service
```

## Reglas de trabajo

- Commits y push solo desde árbol Git en `/opt/easynodeone/app`.
- Deploy prod IIUS: `git pull origin iius-product` + deps + migraciones schema + `systemctl restart nodeone.service`.
- No merge automático `develop`/`main` ↔ `iius-product` sin acuerdo explícito.
