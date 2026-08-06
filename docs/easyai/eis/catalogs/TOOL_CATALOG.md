# Tool Catalog (EIS)

| Campo | Valor |
|-------|--------|
| Versión | **1.0.0** |
| Norma | EIS-003 |

Herramientas **canónicas** (nombres estables). Implementación = Connectors.

| tool_id | capability | side_effect | Familia | Candidatos |
|---------|------------|-------------|---------|------------|
| `tenant.get_organization` | `tenant.read` | read | Consultar | EN1 |
| `identity.get_actor` | `identity.read` | read | Consultar | EN1, ARP |
| `product.get_surface` | `product.read` | read | Consultar | EN1 |
| `customer.search` | `customer.read` | read | Consultar | EN1, EPosOne |
| `customer.get` | `customer.read` | read | Consultar | EN1, EPosOne |
| `crm.list_open_items` | `crm.read` | read | Consultar | ARP, ECRM |
| `membership.verify` | `membership.verify` | read | Consultar | EN1 |
| `membership.list_plans` | `membership.read` | read | Consultar | EN1 |
| `license.list` | `license.read` | read | Consultar | EPosOne |
| `license.list_expiring` | `license.read` | read | Consultar | EPosOne |
| `payment.get_mix` | `payment.read` | read | Consultar | EPosOne |
| `payment.list_pending` | `payment.read` | read | Consultar | EN1, EPosOne |
| `commerce.get_day_board` | `commerce.read` | read | Consultar | EPosOne |
| `commerce.list_exceptions` | `commerce.read` | read | Consultar | EPosOne |
| `commerce.get_shift` | `commerce.read` | read | Consultar | EPosOne |
| `commerce.get_order` | `commerce.read` | read | Consultar | EPosOne |
| `dashboard.get_kpis` | `dashboard.read` | read | Analizar | EPosOne, EN1 |
| `analytics.get_kpis` | `analytics.read` | read | Analizar | multi |
| `subscription.list_active` | `subscription.read` | read | Consultar | EN1 |
| `entitlement.get_effective` | `entitlement.read` | read | Consultar | EN1 |
| `history.list` | `audit.read` | read | Consultar | EN1 |
| `marketing.get_campaign_stats` | `marketing.read` | read | Analizar | ARP |
| `marketing.list_campaigns` | `marketing.read` | read | Consultar | ARP |

### Write / admin (reservados — no default S2 sin GO)

| tool_id | capability | side_effect | Nota |
|---------|------------|-------------|------|
| `commerce.close_shift` | `commerce.write` | write | Requiere GO producto |
| `membership.approve` | `membership.write` | admin | Relatic/EN1 |
| `campaign.publish` | `marketing.write` | publish | ARP |

S1 cataloga; **no autoriza** implementación write.
