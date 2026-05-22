# Etapa 1 — Normalización pagos: estado y cierre

## Hecho (operativo)

| Fase | Estado |
|------|--------|
| 1 Matriz `organization_payment_methods` | Checkout y API usan solo `enabled` en matriz |
| 3 Validación backend | `is_method_enabled` en `create-payment-intent` |
| 4 Perfiles tenant | `panama` / `international` en Admin → Pagos → **Aplicar perfil** |
| Guardado credenciales | `PaymentConfig` sin escribir `*_enabled` desde el panel (sync desde matriz) |

## Legacy (compat, no manda checkout)

- `PaymentConfig.yappy_manual_enabled` / `intl_wire_enabled`: espejo vía `sync_legacy_payment_config_flags`.
- `PAYMENT_METHODS` en `payment_processors.py`: etiquetas/catálogo.
- Migración one-shot: `migrate_organization_payment_methods.py` con `inherit_enabled_from_config=True`.

## Pendiente negocio / QA

- Checklist manual ítems 1–6 firmados en `ETAPA1_DEV_CHECKLIST.md`.
- PayPal live (ítem 8) por tenant.
- Yappy: N/A IIUS.
- Ítems 9–11 si aplica el silo.

## Validación

```bash
cd backend && source ../.venv/bin/activate
python3 run_etapa1_dev_validation.py   # 22 OK DEV; IIUS mono-tenant sin FAIL en [5]
python3 verify_payments_tenant_setup.py
python3 scripts/test_academic_enrollment_iius.py
```

## Perfiles

| Clave | Uso |
|-------|-----|
| `panama` | PayPal + Yappy + Banco General |
| `international` | PayPal + SWIFT (IIUS) |

API: `POST /api/admin/payments/org-methods/apply-profile` body `{ "profile": "international" }`.
