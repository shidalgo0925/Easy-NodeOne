# IIUS — preparación infraestructura

Estado en host `vmi3215083` (2026-05-27). La línea viva sigue siendo **`iius-product`** en `/opt/easynodeone/app`.

## Hoy (silo único)

| Componente | Ruta / valor |
|------------|----------------|
| Código + Git | `/opt/easynodeone/app` → rama `iius-product` |
| Runtime | `nodeone.service` → `WorkingDirectory=/opt/easynodeone/app/backend` |
| Config | `/opt/easynodeone/app/.env` |
| BD | SQLite `instance/NodeOne.db` |
| Uploads | `static/uploads/` |
| Backups freeze | `/opt/easynodeone/backups/iius-freeze-20260527_*` |

**No usar como runtime IIUS:** `/var/www/nodeone` (otro despliegue histórico).

## Objetivo futuro

```
/opt/iius/
  dev/app      → rama develop o iius-product (sandbox)
  staging/app  → main o iius-product pre-prod
  prod/app     → main o iius-product estable
```

Cada silo: propio `.env`, `instance/`, venv, systemd unit, dominio.

## Checklist antes de separar entornos

1. **Git limpio** en `iius-product` (sin detached HEAD ni WIP sin commit).
2. **Tags de hito** publicados (`iius-resources-v1`, `iius-lead-capture-v1`, …).
3. **Smokes en prod** (ejecutar desde `backend/`):
   - `python scripts/smoke_iius_catalog_events.py`
   - `python scripts/smoke_iius_payments_ops.py`
   - `python scripts/test_academic_gate_iius.py`
   - Matriz acceso real (10 casos) documentada en chat/ops.
4. **Backup** `.env` + `instance/` + `static/uploads/` antes de cualquier migración.
5. **Postgres:** solo tras dump/restore probado en staging; no cortar SQLite en prod sin ventana.

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

## Reglas de trabajo

- Commits y push solo desde árbol Git en `/opt/easynodeone/app`.
- Deploy prod IIUS: `git pull origin iius-product` + deps + migraciones schema + `systemctl restart nodeone.service`.
- No merge automático `develop`/`main` ↔ `iius-product` sin acuerdo explícito.
