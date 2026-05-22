# Etapa 2 — IIUS (runbook)

**Prerrequisito:** Etapa 1 DEV con **GO** (`run_etapa1_dev_validation.py` OK + commit `046e991` o posterior en `develop`).

**Baseline IIUS histórico:** `b605a78` · **Rama a desplegar:** `develop` (~77 commits después al 2026-05).

**No copiar** filas `organization_payment_methods` ni `payment_config` desde DEV: semillar **solo la org IIUS** en su Postgres.

---

## 1. Pre-vuelo (obligatorio)

```bash
# En el silo IIUS (ej. /opt/easynodeone/prod/app — confirmar ruta real)
git fetch origin
git rev-parse HEAD
git log -1 --oneline

# Backup BD IIUS (ajustar DATABASE_URL del .env IIUS)
pg_dump "$DATABASE_URL" -Fc -f /opt/easynodeone/backups/iius_pre_etapa2_$(date +%Y%m%d).dump

# Tag rollback código (opcional)
git tag iius-pre-etapa2-$(date +%Y%m%d) HEAD
```

Anotar:

- `organization_id` de IIUS en `saas_organization` (suele ser `1`).
- Dominio / subdominio (host-lock).
- Servicio systemd (ej. `easynodeone` / `gunicorn`).

---

## 2. Deploy código

```bash
cd <IIUS_APP_ROOT>
git checkout develop
git pull origin develop
# Debe incluir al menos: e63cced, ee33766, b0ede24, 046e991
source <venv>/bin/activate
sudo systemctl restart <servicio-iius>
```

---

## 3. Migraciones / bootstrap (orden sugerido)

```bash
cd <IIUS_APP_ROOT>/backend
source <venv>/bin/activate

python3 migrate_yappy_manual_checkout_v3.py    # si payment_config sin columnas Yappy
python3 migrate_intl_wire_config.py          # si aplica
python3 migrate_organization_payment_methods.py
python3 migrate_security_matrix_module.py
python3 provision_payment_config_tenants.py    # solo crea config si falta; revisar org IIUS
```

Bootstrap en arranque (`bootstrap_nodeone_schema`) también crea matriz + configs faltantes.

---

## 4. Semilla solo tenant IIUS

```bash
# Sustituir OID por el id real de IIUS
export IIUS_ORG_ID=1

python3 <<'PY'
import os, sys
sys.path.insert(0, os.getcwd())
from app import app, db
from nodeone.services import organization_payment_methods as opm
from nodeone.services.payment_config_provision import dedicated_active_config, provision_missing_payment_configs

OID = int(os.environ.get("IIUS_ORG_ID", "1"))
with app.app_context():
    opm.ensure_organization_payment_methods_schema()
    opm.seed_organization_payment_methods(OID)  # sin inherit desde otras orgs
    if dedicated_active_config(OID) is None:
        provision_missing_payment_configs(source_org_id=OID, target_org_ids=(OID,))
    opm.sync_legacy_payment_config_flags(OID)
    ctx = opm.build_checkout_payment_context(OID)
    print("IIUS org", OID, "checkout:", list(ctx["payment_methods"].keys()))
PY

python3 verify_payments_tenant_setup.py
python3 run_etapa1_dev_validation.py   # revisar solo filas de org IIUS en salida
```

Ajustar matriz en **Admin → Pagos** (org IIUS, **Aplicar** en selector) según negocio IIUS.

---

## 5. Pruebas IIUS (mismo checklist que DEV)

Usar `docs/ETAPA1_DEV_CHECKLIST.md` ítems 1–6 en el dominio IIUS.

---

## 6. Rollback

| Tipo | Acción |
|------|--------|
| Código | `git checkout iius-pre-etapa2-YYYYMMDD` o `b605a78` + restart |
| BD | `pg_restore` del dump pre-vuelo |

---

## 7. Fuera de alcance Etapa 2

- Landing marketing (`landing/`).
- Matriz Odoo (`security_matrix_manager`) salvo que IIUS use Odoo en prod.
- Copiar tenants 2–4 de DEV.

---

## Contacto

| Fecha | Quién | Resultado |
|-------|-------|-----------|
| | | |
