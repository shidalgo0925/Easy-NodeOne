# IIUS — GO operativo (servidor)

**Estado:** GO técnico + Git **cerrado** · Fase 3 (PayPal live + QA manual) **pendiente**

| Ref | Valor |
|-----|--------|
| Tag / prod | `iius-go-20260522` → **`9330cfc`** |
| DEV / `origin/develop` | **`9330cfc`** (merge `release/iius-go-20260522`) |
| Silo | `/opt/easynodeone/app` · org **1** |

## Backend (hecho)

| Ítem | Estado |
|------|--------|
| Código en prod = tag = develop | OK (`9330cfc`) |
| Matriz pagos + perfil Internacional | OK |
| `registration_policy = academic_closed` | OK |
| Programas inscripción (4 diplomados + taller) | OK en BD |
| CRUD admin programas | OK |
| Branding IIUS + menú Usuarios | OK (en release) |
| `run_etapa1_dev_validation.py` | LISTO (IIUS mono-tenant) |
| Host → org 1 | `subdomain=iius` |
| `go_iius_validate_all.sh` en IIUS | OK (gate incluido) |
| Pago OK → matrícula `confirmed` | OK (código + reconcile) |

## Fase 3 — pendiente negocio

| Ítem | Doc |
|------|-----|
| PayPal live (Client ID + Secret) | `IIUS_PAYPAL_LIVE.md`, `IIUS_FASE3_PAYPAL_Y_QA.md` |
| QA manual dominio IIUS | `IIUS_FASE3_PAYPAL_Y_QA.md` § B |
| Yappy | N/A IIUS |

## Scripts

```bash
cd /opt/easynodeone/app/backend
bash scripts/go_iius_validate_all.sh
python3 scripts/check_paypal_readiness_iius.py
```

## Rollback

`docs/ETAPA2_IIUS_RUNBOOK.md` §6 · tag `iius-pre-etapa2-20260522`
