# Connector Catalog (EIS)

| Campo | Valor |
|-------|--------|
| Versión catálogo | **1.0.0** |
| Norma | EIS-001 / EIS-006 |
| Estado | Seed S1 — **declarativo** (no implica runtime ready) |

---

## Entradas planificadas ecosistema ETS

| connector_id | product_code | Nombre | Owner | Lifecycle S1 | Notas |
|--------------|--------------|--------|-------|--------------|-------|
| `en1-platform` | `en1` | EN1 Platform | CODITO | `declared` | Tenant, apps, entitlements, history, event outbox |
| `eposone` | `eposone` | EPosOne | CODITO | `declared` | Commerce, cash, devices, OCC/dashboard |
| `em-accion` | `em-accion` | EM+Acción / ARP | ARP | `declared` | Marketing context, campaigns, AI gateway side |
| `emembership` | `emembership` | EMembership | CODITO | `declared` | Membership verify/plans (puede vivir bajo en1) |
| `ecrm` | `ecrm` | ECRM | CODITO | `declared` | Limited hasta app real |

---

## Campos operativos (cuando pasen a registered)

Para cada connector en operación se completará: `manifest_url` por ambiente, `health_url`, contacto on-call.

S1 no asigna URLs de producción como “ready”.
