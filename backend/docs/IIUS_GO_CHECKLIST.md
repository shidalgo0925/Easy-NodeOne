# IIUS — GO operativo (servidor)

**Estado: GO técnico cerrado** (2026-05-22)

Fecha referencia: 2026-05-22 · Silo: `/opt/easynodeone/app` · Org **1**

## Backend

| Ítem | Estado |
|------|--------|
| Código base `63203e6` + parches locales | OK |
| Matriz pagos + perfil Internacional | OK |
| `registration_policy = academic_closed` | OK |
| Programas inscripción (4 diplomados + taller demo en BD) | semillas `seed_academic_programs_iius_all.py` |
| CRUD admin programas | OK |
| Branding IIUS + menú Usuarios | OK (local, pendiente commit `develop`) |
| `run_etapa1_dev_validation.py` | LISTO (mono-tenant) |
| Matrícula demo user 1 (reconcile) | `confirmed` + campus desbloqueado |
| `verify_payments_tenant_setup.py` | OK con `NODEONE_BRAND_PRESET=iius` |
| Host `apps.internationalinstitute.us` → org 1 | `subdomain=iius` (`bootstrap_iius_org_host.py`) |
| Pago OK → matrícula `confirmed` | `process_academic_program_items_after_payment` |

## Pendiente negocio (no bloquea GO técnico)

| Ítem | Responsable |
|------|-------------|
| PayPal live en Admin → Pagos | Negocio |
| Commit/push `develop` desde `dev/app` | Tarball → `dev@194.60.201.29:/tmp/` · `IIUS_TRANSFER_TO_DEV.md` · `dev_apply_iius_tarball.sh` |
| IIUS prod tras tag en remoto | `git checkout iius-go-20260522` + restart · runbook §2–4 + PayPal live |
| Yappy | N/A IIUS |

## Scripts útiles

```bash
cd /opt/easynodeone/app/backend && bash scripts/go_iius_validate_all.sh
# o manual:
cd /opt/easynodeone/app/backend && source ../.venv/bin/activate
export NODEONE_BRAND_PRESET=iius
python3 run_etapa1_dev_validation.py
python3 verify_payments_tenant_setup.py
python3 scripts/test_academic_enrollment_iius.py
python3 scripts/test_academic_gate_iius.py
python3 scripts/test_iius_inscripcion_landings.py
python3 scripts/reconcile_academic_enrollments_paid.py
python3 scripts/seed_academic_programs_iius_all.py 1
python3 scripts/bootstrap_iius_org_host.py 1
python3 scripts/check_paypal_readiness_iius.py  # exit 2 = falta client_id live
```

## Rollback

Ver `docs/ETAPA2_IIUS_RUNBOOK.md` §6.
