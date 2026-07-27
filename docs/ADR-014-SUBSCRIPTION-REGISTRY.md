# ADR-014 — Subscription Registry (tenant ↔ producto ETS)

| Campo | Valor |
|-------|--------|
| ID | ADR-014 |
| Título | Subscription Registry V1 — relación tenant-producto |
| Estado | **Aprobado (GO)** — 24 jul 2026 · **Implementado en Dev** |
| Ámbito | EN1 Platform · Portal ETS (consumidor futuro) · productos ETS |
| Relacionados | [ADR-012](ADR-012-ETS-ECOSYSTEM-ARCHITECTURE.md) · [ADR-013](ADR-013-PORTAL-ETS-PUNTO-ENTRADA.md) · [ADR-011](ADR-011-PORTAL-ETS-PUNTO-ENTRADA.md) · License Engine V1 |

---

## Decisión

Se introduce el **Subscription Registry** como capa independiente que responde:

> ¿Qué productos ETS tiene contratados o habilitados este tenant?

**Producto ≠ Suscripción ≠ Licencia.**

| Capa | Pregunta |
|------|----------|
| ContextResolver | ¿Qué producto corresponde al dominio? |
| Product Registry | ¿Qué productos ETS existen? |
| App Registry | ¿Qué apps técnicas componen el producto? |
| **Subscription Registry** | **¿Qué productos tiene este tenant?** |
| License Engine | ¿Puede operar el producto/dispositivo ahora? |

---

## Modelo

- Tenant oficial EN1 = `saas_organization.id` (`organization_id`).
- No se crea entidad tenant paralela.
- Tabla: `ets_product_subscription`.
- **Una fila por** `(organization_id, product_code)` (unique).
- Historial = transición de `status` en la misma fila (no múltiples abiertas).

Campos: `status`, `starts_at`, `ends_at`, `trial_ends_at`, `reason`, `metadata_json`, auditoría de usuario, timestamps.

Solo se persiste `product_code` (referencia a Product Registry). **No** se duplican nombre, dominio, icono, theme ni `app_ids`.

---

## Estados

`PENDING` · `TRIAL` · `ACTIVE` · `PAST_DUE` · `SUSPENDED` · `CANCELLED` · `EXPIRED`

Entitled (habilitado comercialmente): `TRIAL` · `ACTIVE` · `PAST_DUE`.

---

## Contrato

`nodeone.core.platform.subscription_registry.SubscriptionRegistry`

- `get` / `get_for_tenant_product` / `list_for_tenant` / `list_active_for_tenant` / `has_product`
- `create_trial` / `activate` / `suspend` / `cancel` / `mark_expired`
- `list_tenant_products` → DTO «Mis productos» (suscripción + ProductRegistry)

Aislamiento: parámetro opcional `scope_organization_id`.

Trial: solo EN1 (`create_trial`); la APK no inventa Trial. License Engine sigue dueño de la licencia por caja.

---

## Relación con License Engine

Unidireccional y mínima: al `suspend`/`cancel` de producto `eposone` (flag `sync_licenses=True`) se propaga suspensión a licencias de caja activas. No se duplica grace, heartbeat ni offline.

---

## Fuera de alcance V1

Portal UI · Marketplace · precios · pagos · branding · menús · DNS portal.

---

## Historial

| Fecha | Nota |
|-------|------|
| **2026-07-24** | GO + implementación Dev (tabla + servicio + tests) |
