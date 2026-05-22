# Etapa 1 DEV — Checklist de cierre

**Entorno:** `appdev.easynodeone.com` · rama `develop` · servicio `easynodeone-dev`  
**IIUS:** congelado hasta marcar este checklist y dar **GO explícito** a Etapa 2.

Commits de referencia (pagos + SaaS matriz):

- `e63cced` — Pagos multi-tenant (matriz, checkout, config por org)
- `ee33766` — Landing, matriz Odoo, RBAC, docs
- `b0ede24` — Módulo `security_matrix` en catálogo SaaS

---

## Antes de probar

1. Menú lateral → elegir **empresa** → **Aplicar** (esperar recarga).
2. Confirmar banner en **Admin → Pagos**: «Empresa activa en este panel» con el id correcto.
3. (Opcional, servidor) `python3 backend/verify_payments_tenant_setup.py` → debe imprimir `OK`.

Scripts útiles en DEV:

```bash
cd /opt/easynodeone/dev/app/backend
source /opt/easynodeone/dev/venv/bin/activate
python3 verify_payments_tenant_setup.py
python3 migrate_organization_payment_methods.py   # solo si falta tabla/filas
python3 provision_payment_config_tenants.py       # solo si falta config dedicada por org
python3 migrate_security_matrix_module.py         # catálogo SaaS security_matrix
```

---

## Checklist funcional

Marcar **OK** / **FAIL** / **N/A** y notas.

| # | Área | Prueba | OK |
|---|------|--------|-----|
| 1 | Matriz pagos | Desactivar `wire_international` → Guardar matriz → checkout **sin** SWIFT | ☐ |
| 2 | Matriz pagos | Reactivar SWIFT → checkout **con** SWIFT | ☐ |
| 3 | Config pagos | Org A: guardar credenciales → Org B: otros datos → guardar sin error | ☐ |
| 4 | Config pagos | Sin cambiar empresa en selector: no guardar en org equivocada | ☐ |
| 5 | Checkout | Métodos visibles = solo **Activo** en matriz | ☐ |
| 6 | API | POST `create-payment-intent` con método desactivado → 400 | ☐ |
| 7 | Yappy manual | Crear pago + comprobante + validación admin (si aplica) | ☐ |
| 8 | PayPal | Intent sandbox/live según config de la org | ☐ |
| 9 | Módulos SaaS | `/admin/saas-modules`: aparece `security_matrix`, toggle por org | ☐ |
| 10 | Matriz Odoo | `/admin/security-matrix`: catálogo/import (si usan Odoo en DEV) | ☐ |
| 11 | RBAC EN1 | `/admin/roles/matrix` (distinto de matriz Odoo) | ☐ |
| 12 | Académico / carrito | Inscripción o checkout de curso crítico para el negocio | ☐ |

---

## Reglas de negocio (recordatorio)

| Qué controla visibilidad en checkout | Qué NO |
|--------------------------------------|--------|
| `organization_payment_methods.enabled` | `intl_wire_enabled`, `yappy_manual_enabled`, checkboxes «mostrar en checkout» |
| Matriz **Activo** en Admin → Pagos (arriba) | `PAYMENT_METHODS` hardcodeado |

`PaymentConfig` = credenciales, cuentas SWIFT, QR Yappy, instrucciones.

---

## Validación automática (servidor)

```bash
python3 run_etapa1_dev_validation.py
```

Última corrida en DEV: **22 OK** — matriz/checkout/config, toggle SWIFT, scope API org=2, `is_method_enabled`, `save_methods_payload`, SaaS `security_matrix`.

Pendiente en navegador: PayPal, Yappy manual, académico (ítems 7–8, 12).

---

## Criterio GO Etapa 1 (DEV listo)

- [x] Ítems 1–6 **OK** (pagos multi-tenant) — verificado en servidor automático.
- [ ] Ítems críticos del negocio (7, 8, 12) **OK** o **N/A** documentado.
- [ ] Sin regresiones bloqueantes en admin por org.
- [ ] Responsable firma fecha: _______________

→ Recién entonces: plan **Etapa 2 IIUS** (migraciones, deploy, semilla solo tenant IIUS, sin copiar orgs de DEV).

---

## Etapa 2 IIUS (no ejecutar aún)

1. Backup BD + tag/commit rollback (`b605a78` o el de prod IIUS).
2. Diff `b605a78..develop` — migraciones y archivos sensibles.
3. Deploy código + migraciones en Postgres IIUS.
4. Semilla matriz pagos + `payment_config` **solo organización IIUS**.
5. Prueba checkout/admin en dominio IIUS (host-lock / sesión).
6. Ventana de rollback documentada.

---

## Contacto / notas de fallo

| Fecha | Org | # ítem | Qué pasó |
|-------|-----|--------|----------|
| | | | |
