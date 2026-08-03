# IIUS — Fase 3: PayPal live + QA manual

**Prerrequisito:** IIUS prod en `iius-go-20260522` (`9330cfc`), `go_iius_validate_all.sh` OK.

## A. PayPal live (negocio)

1. [developer.paypal.com](https://developer.paypal.com) → app **Live** → Client ID + Secret.
2. En PayPal app, URLs permitidas:
   - Return: `https://apps.internationalinstitute.us/payment/paypal/return`
   - Cancel: `https://apps.internationalinstitute.us/payment/paypal/cancel`
3. Admin IIUS → **Pagos** → selector org **1** → **Aplicar**.
4. Completar **Client ID**, **Client Secret**, modo **live** → **Guardar**.
5. Verificar en servidor:

```bash
cd /opt/easynodeone/app/backend
source ../.venv/bin/activate
export NODEONE_BRAND_PRESET=iius
python3 scripts/check_paypal_readiness_iius.py   # debe exit 0
```

6. Prueba real: inscripción → login → checkout → PayPal (dominio `api-m.paypal.com`, no demo).

## B. QA manual inscripción + campus

| # | Prueba | Esperado |
|---|--------|----------|
| 1 | `/inscripcion/neuro-liderazgo-intercultural` anónimo | 200, planes visibles |
| 2 | Elegir plan → login/registro | Redirige con `next=` a continuar |
| 3 | Checkout PayPal (o demo si sin live) | Pago creado |
| 4 | Tras pago OK | Matrícula `confirmed` en admin o `reconcile_academic_enrollments_paid.py` |
| 5 | Miembro sin matrícula | No **Explorar**; sí **Mi campus** + CTA inscripción |
| 6 | Miembro con matrícula | Campus + servicios según módulos |
| 7 | Admin | **Educación → Programas inscripción** edita slug publicado |

## C. Cierre Fase 3

- [ ] `check_paypal_readiness_iius.py` → exit 0
- [ ] Un pago live (o demo firmado por negocio) documentado
- [ ] Checklist B ítems 1–7 probados en dominio IIUS
