# Validación EIS × EN1 · EPosOne · EM+Acción

| Campo | Valor |
|-------|--------|
| Norma | EIS 1.0.0 |
| Fecha | 5 ago 2026 |
| Método | Contraste con arquitectura/inventario existente — **sin asumir código futuro** |

---

## 1. Pregunta

¿Pueden EN1, EPosOne y EM+Acción implementar Connectors EIS-conformes **sin romper** su arquitectura actual?

---

## 2. EN1 Platform

| Requisito EIS | ¿Cubrible hoy? | Evidencia / gap |
|---------------|----------------|-----------------|
| Contextos sin SQL | **Sí** | OrganizationService, ContextResolver, Entitlement/Subscription registries |
| Tools read | **Sí** | History API, master APIs, dashboard services |
| Events | **Sí** | `platform_domain_event` outbox + sync pull |
| Auth tenant | **Sí** | session org + futuro service token (contrato EIS-005) |
| Manifest / Discovery | **Pendiente** | No existe well-known; **no bloquea** arquitectura — es capa aditiva |
| CRM connector rico | **Limitado** | ecrm stub → capability `crm.read` limitada o omitida |

**Veredicto EN1:** Compatible. EIS se apoya en servicios/facades existentes. No requiere rediseñar Core ni multi-tenant.

---

## 3. EPosOne

| Requisito EIS | ¿Cubrible hoy? | Evidencia / gap |
|---------------|----------------|-----------------|
| Commerce contexts | **Sí** | OCC + CommerceDashboardService |
| Tools caja/pedido | **Sí** | Order Domain, cash shifts, OCC builders |
| Events | **Sí** | eposone/commerce domain events + order timeline |
| Licenses | **Sí** | register license services |
| Devices health | **Sí** | `last_seen_at` vía servicios dispositivos |
| Write tools | **Posible** | Existen mutaciones BO/API; EIS las deja fuera hasta GO |

**Veredicto EPosOne:** Compatible. EPosOne ya es dominio rico; el Connector es fachada, no nuevo dominio comercial. Dual mode Standalone/Integrado: Manifest puede declarar `environments` y `base_url` por modo sin cambiar Order Domain.

---

## 4. EM+Acción (ARP)

| Requisito EIS | ¿Cubrible hoy? | Evidencia / gap |
|---------------|----------------|-----------------|
| Marketing contexts | **Sí (lado ARP)** | Inventory ARP: Marketing Context Engine, Company Brain, Campaigns |
| Tools campañas | **Sí (lado ARP)** | Publishing / analytics de campaña (según ARP) |
| Events campañas | **Sí (declarable)** | `Marketing.CampaignPublished`, etc. |
| AI Gateway | **Fuera EIS** | Gateway/providers son EasyAI/ARP internals — **no** se sustituyen por Connector |
| Consumir EN1 | **Vía EasyAI** | ARP no necesita SQL a EN1; EasyAI orquesta Connectors |

**Veredicto EM+Acción:** Compatible. ARP aporta Connectors de marketing + infra IA; no debe exponer LiteLLM como “Connector de negocio”. Separación: **Connector = datos/acciones de marketing**; **Gateway = runtime LLM**.

---

## 5. Riesgos de conformidad (compartidos)

1. Duplicar Gateway LLM dentro de un Connector de producto.
2. Exponer SQL “para que el modelo consulte”.
3. Un solo Connector monolítico ilegible (preferir capabilities claras).
4. Ignorar `organization_id` / tenant claim.
5. Tratar el borrador `nodeone.core.easyai` como norma en lugar del EIS.

---

## 6. Conclusión

| Producto | ¿Puede implementar EIS sin romper arquitectura? |
|----------|--------------------------------------------------|
| EN1 | **Sí** |
| EPosOne | **Sí** |
| EM+Acción | **Sí** |

El EIS es **aditivo**: capa de contrato sobre servicios existentes. Ningún producto está obligado a reescribir su core para S1 (solo documentación). La implementación de Connectors es sprint posterior.
