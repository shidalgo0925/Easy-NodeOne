# IIUS — GO operativo (servidor)

**Estado actual:** ver **`IIUS_CIRCUIT_STATUS.md`** (fuente única de verdad).

**GO técnico:** cerrado (2026-05-22) · Código: **`9330cfc`** / tag **`iius-go-20260522`** · Silo: `/opt/easynodeone/app` · Org **1**

---

## Backend (IIUS prod)

| Ítem | Estado |
|------|--------|
| Código `9330cfc` (tag `iius-go-20260522`) | OK |
| Matriz pagos + perfil Internacional | OK |
| `registration_policy = academic_closed` | OK |
| Programas inscripción (4 diplomados + taller demo en BD) | OK — `seed_academic_programs_iius_all.py` |
| CRUD admin programas | OK |
| Branding IIUS + menú Usuarios | OK en release `develop` |
| `go_iius_validate_all.sh` | OK en IIUS (gate, landings, pagos) |
| Matrícula demo user 1 (reconcile) | OK en IIUS mono-tenant |
| Host `apps.internationalinstitute.us` → org 1 | OK — `subdomain=iius` |
| Pago OK → matrícula `confirmed` | OK |

---

## Pendiente negocio (no bloquea GO técnico)

| Ítem | Responsable | Doc |
|------|-------------|-----|
| PayPal live (Client ID + Secret, org 1) | Negocio | `IIUS_PAYPAL_LIVE.md` |
| Prueba inscripción + pago + campus en dominio IIUS | Negocio / QA | `ETAPA1_DEV_CHECKLIST.md` ítems 7–8, 12 |
| Yappy | N/A IIUS | — |

**Git / DEV:** merge y tag hechos — no requiere tarball ni nuevo push salvo docs o fixes.

---

## Scripts útiles

```bash
cd /opt/easynodeone/app/backend && bash scripts/go_iius_validate_all.sh
# o manual:
cd /opt/easynodeone/app/backend && source ../.venv/bin/activate
set -a && source ../.env && set +a
export NODEONE_BRAND_PRESET=iius
python3 run_etapa1_dev_validation.py
python3 verify_payments_tenant_setup.py
python3 scripts/test_academic_enrollment_iius.py
python3 scripts/test_academic_gate_iius.py
python3 scripts/test_iius_inscripcion_landings.py
python3 scripts/reconcile_academic_enrollments_paid.py
python3 scripts/seed_academic_programs_iius_all.py 1
python3 scripts/bootstrap_iius_org_host.py 1
python3 scripts/check_paypal_readiness_iius.py  # exit 0 = listo live; 2 = falta client_id
```

---

## Rollback

Ver `ETAPA2_IIUS_RUNBOOK.md` §6.
