# Capability Catalog (EIS)

| Campo | Valor |
|-------|--------|
| Versión | **1.0.0** |
| Norma | EIS-000 / EIS-005 scopes |

Una **capability** agrupa Contextos, Tools y Events relacionados.

| capability | Descripción | Acceso típico |
|------------|-------------|----------------|
| `tenant.read` | Leer organización/tenant | read |
| `identity.read` | Leer identidad usuario | read |
| `product.read` | Producto/surface/brand | read |
| `customer.read` | Clientes/contactos | read |
| `crm.read` | CRM | read |
| `crm.write` | Mutaciones CRM | write |
| `membership.read` | Membresías | read |
| `membership.verify` | Verificación | read |
| `membership.write` | Altas/cambios | write |
| `license.read` | Licencias | read |
| `license.events` | Eventos licencia | events |
| `payment.read` | Pagos | read |
| `payment.events` | Eventos pago | events |
| `commerce.read` | Comercio/POS | read |
| `commerce.write` | Mutaciones POS | write |
| `commerce.events` | Eventos comercio | events |
| `analytics.read` | Analytics | read |
| `dashboard.read` | Dashboards | read |
| `subscription.read` | Suscripciones | read |
| `subscription.events` | Eventos suscripción | events |
| `entitlement.read` | Entitlements | read |
| `audit.read` | Historial/auditoría | read |
| `audit.events` | Eventos audit | events |
| `marketing.read` | Marketing/campañas | read |
| `marketing.write` | Publicar campañas | write |
| `marketing.events` | Eventos marketing | events |
| `platform.admin` | Cross-tenant (futuro) | admin |

Scope EIS-005: `eis:{capability}:invoke` o `eis:{capability}:subscribe`.
