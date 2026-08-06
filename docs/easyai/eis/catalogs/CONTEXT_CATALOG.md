# Context Catalog (EIS)

| Campo | Valor |
|-------|--------|
| Versión | **1.0.0** |
| Norma | EIS-002 |

Catálogo **canónico** de `context_id`. Los productos publican un subconjunto.

| context_id | capability | Descripción | Productos candidatos |
|------------|------------|-------------|----------------------|
| `organization.current` | `tenant.read` | Tenant/org activa | EN1, EPosOne, ARP |
| `user.actor` | `identity.read` | Usuario en cuyo nombre se actúa | EN1, ARP |
| `product.surface` | `product.read` | Producto/surface/brand de host | EN1 |
| `customer.summary` | `customer.read` | Resumen cliente/contacto | EN1, EPosOne, ARP |
| `crm.pipeline_summary` | `crm.read` | Resumen CRM | ARP, ECRM (futuro) |
| `membership.scope` | `membership.read` | Alcance membresía | EN1/EMembership, Relatic |
| `license.summary` | `license.read` | Resumen licencias | EPosOne, EN1 |
| `payment.mix_period` | `payment.read` | Mix de pagos período | EPosOne, EN1 |
| `commerce.day_summary` | `commerce.read` | Día operativo POS | EPosOne |
| `analytics.kpi_snapshot` | `analytics.read` | KPIs | EPosOne, ARP, EN1 |
| `dashboard.operational` | `dashboard.read` | Snapshot dashboard | EPosOne, EN1 |
| `campaign.performance` | `marketing.read` | Rendimiento campañas | ARP / EM+Acción |
| `subscription.summary` | `subscription.read` | Suscripciones producto | EN1 |

Extensiones: prefijo `x.{product}.…` hasta promoción a canónico en MINOR del catálogo.
