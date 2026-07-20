# Commercial Policy Engine — Infraestructura EN1 V1

| Campo | Valor |
|-------|--------|
| Estado | **Implementación infra** — 19 jul 2026 (Dev EN1) |
| Roadmap | [`EN1_PLATFORM_EPOSONE_V6_ROADMAP.md`](EN1_PLATFORM_EPOSONE_V6_ROADMAP.md) |
| Instrucción | Sprint V6 — preparar administrador central de políticas (sin lógica de cálculo) |
| ADR | [`ADR-008-EPOSONE-COMMERCIAL-ENGINE.md`](ADR-008-EPOSONE-COMMERCIAL-ENGINE.md) |
| Código | `models/eposone_commercial_policy.py` · `commercial_policy_service.py` · `order_calculation_engine.py` · schema DDL |

---

## Objetivo

Preparar EN1 para administrar **políticas comerciales versionadas** de EPosOne en modo Integrado.

**No** implementa motores Fiscal / Propinas / Pagos / Comercial / Totales definitivos.

---

## Dual Mode

| Modo | Quién administra políticas |
|------|----------------------------|
| Standalone | EPosOne (local) — EN1 no asume que todos los POS estén conectados |
| Integrado | EN1 es source of truth; POS descarga vigentes |

---

## Tipos de política (genéricos)

| `policy_type` | Uso |
|---------------|-----|
| `fiscal` | Contrato Fiscal |
| `tips` | Contrato Propinas |
| `payments` | Contrato Pagos |
| `receipt` | Contrato Recibo |
| `commercial_config` | Configuración comercial / caja |
| `promotion` | Promociones (futuro; tipo reservado) |

Un solo motor; no módulos aislados por tema.

---

## Modelo de datos

1. **`eposone_commercial_policy`** — identidad (org, tipo, código, nombre, activo, vigencia).
2. **`eposone_commercial_policy_version`** — cada cambio = nueva versión (`version_number`, `payload_json`, `publication_status`, `is_current`).
3. **`eposone_commercial_policy_assignment`** — asignación por alcance.
4. **`eposone_commercial_policies_sync_state`** — `policies_version` monótono por org (sync incremental).

### Ciclo de vida de publicación (`publication_status`)

| Estado | POS |
|--------|-----|
| `draft` | No |
| `active` | Sí (única vigente por política) |
| `obsolete` | No (histórico) |
| `archived` | No |

Crear versión → **draft**. Publicar → valida → **active**; la active previa pasa a **obsolete**.

### Alcance (`scope_type`)

`organization` → `branch` → `pos` → `register`

Herencia: gana la asignación **más específica** activa para ese `policy_type`.  
Override en nivel inferior sobrescribe el superior.

### Auditoría

Eventos de dominio (`AuditService`), entre otros:

- `eposone.commercial_policy.created`
- `eposone.commercial_policy.version_created`
- `eposone.commercial_policy.version_published`
- `eposone.commercial_policy.version_archived`
- `eposone.commercial_policy.activated` / `deactivated`
- `eposone.commercial_policy.assigned`
- `eposone.commercial_policy.synced` (cuando el bootstrap envía políticas nuevas)

### Categorías fiscales en producto (PA)

Campo `core_product.fiscal_category`:

| Código | ITBMS | Uso |
|--------|-------|-----|
| `ITBMS_7` | 7% | General (default) |
| `ITBMS_10` | 10% | Bebidas alcohólicas / hospedaje (DGI) |
| `ITBMS_15` | 15% | Tabaco |
| `EXENTO` | 0% | Exentos |

Seed política `PA-ITBMS-V1` (tipo `fiscal`, publicada). Al agregar ítem al pedido, si no viene `tax`, EN1 calcula ITBMS desde la categoría del producto.

Ver: `nodeone/modules/eposone/fiscal_categories.py`

---

## Sync / Bootstrap

- Query: `?policies_version=<n>` (igual espíritu que `cashiers_version`).
- Respuesta siempre incluye `policies_version`.
- Si `known == vigente` → `policies_changed: false` y **no** reenvía el listado completo.
- Si cambió → solo políticas con versión **active** + `policy_bundles`.
- Claves nuevas son **adicionales**; clientes viejos las ignoran.

`include=policies` opcional; por defecto se incluyen con el bootstrap estándar.

---

## Order Calculation Engine

Interfaz preparada: `OrderCalculationEngine.calculate(...)`.

Hoy responde `status=not_implemented` hasta aprobación de contratos V6 + T1. **No** calcula totales.

---

## Criterio de cierre (esta infra)

- [x] Tablas + servicio de políticas versionadas  
- [x] Asignación Empresa/Sucursal/POS/Caja + herencia  
- [x] Sync incremental por `policies_version`  
- [x] Bootstrap compatible  
- [x] Stub Totales  
- [x] Dual Mode respetado (EN1 admin solo en Integrado)  
- [x] Ciclo Draft/Active/Obsolete/Archived  
- [x] Auditoría de cambios  
- [x] Validación pre-publicación  
- [x] Sin datos `INFRA-TEST-*` en develop  

---

*Infra V6. Lógica de negocio de cada contrato = fases posteriores post-aprobación.*
