# EN1 ADR-037 — Inventario M2M / Integration Surfaces

| Campo | Valor |
|-------|--------|
| ADR | [ADR-037](ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md) |
| Tipo | **Inventario** (discovery) — sin refactor / sin F1 Integration Center |
| Fecha | 2026-08-13 |
| Entorno inspeccionado | Dev EN1 `/opt/easynodeone/dev/app` · rama `develop` |
| Estado | **DONE (docs)** · F1–F3 OFF hasta ACCEPT SPAGHETTI + GO impl |
| PRD | **Bloqueado** — M2M comercial PROD hasta F1–F3 + E2E `credential_ref` |

---

## 1. Resumen ejecutivo

EN1 hoy tiene **varias superficies** de integración; solo un subconjunto es «M2M Integration API Key» (`X-API-Key` → `integration_api_key`):

| Familia | Auth | ¿Integration Center? | Consumidores |
|---------|------|----------------------|--------------|
| **A. Integration API Key** | `X-API-Key` | Sí (API Center) | ESB commercial · Odoo membership verify |
| **B. Landing public** | `PUBLIC_LANDING_API_KEY` | **No** | Landing / OCI |
| **C. EPosOne device** | Device Bearer / provisioning | **No** | EP1 tablet |
| **D. PSP / Odoo outbound** | Stripe sig · Odoo Bearer/HMAC | **No** | Stripe · Odoo ERP |

**Hueco central ADR-037:** no existe entidad `Integration` (producto + env + health + scopes). Keys planas por org; commercial bridge **no** está en el catálogo del API Center.

---

## 2. Endpoints M2M (familia A — Integration API Key)

Auth compartida: `nodeone/services/integration_api_keys.py` (SHA-256). Log: `integration_api_access_log`.

| Method | Path | Consumer | Notas |
|--------|------|----------|-------|
| `POST` | `/api/v1/commercial/bootstrap` | **ESB** | Idempotency-Key opcional |
| `POST` | `/api/v1/commercial/checkout` | **ESB** | Idempotency-Key opcional |
| `POST`/`GET` | `/api/v1/commercial/quote` | **ESB** | Sin tabla idempotency |
| `GET` | `/api/v1/commercial/payment-methods` | **ESB** | Org = key / provider ETS |
| `GET` | `/api/v1/commercial/entitlement` | **ESB** | `product_code`, `customer_id` |
| `POST` | `/api/v1/membership/verification` | **Odoo / B2B** | Solo `X-API-Key` (Bearer ignorado) |

**Código:** `nodeone/modules/commercial_bridge/` · `membership_verification/`.

**Gap:** commercial **no** listado en `API_CATALOG` del API Center (solo membership_verification).

---

## 3. Superficies adyacentes (no confudir con Integration Center)

### B. Landing (`public_api`)

| Method | Path | Auth |
|--------|------|------|
| `POST` | `/api/public/demo-request` | Ninguna (CORS) |
| `GET` | `/api/public/services` (+ id) | `X-Landing-Api-Key` / Bearer |
| `POST` | `/api/public/book-service` | same + Idempotency-Key |
| `POST` | `/api/public/request-quote` | same + Idempotency-Key |

Env: `PUBLIC_LANDING_API_KEY` · `PUBLIC_LANDING_ORG_ID` — **fuera** de `integration_api_key`.

### C. EPosOne

Prefijos `/api/v1/devices|orders|cash|onboarding|activation/*` — Device Bearer / activation tokens. **No** es M2M Integration Center.

### D. Webhooks / outbound

| Dirección | Pieza | Peer |
|-----------|-------|------|
| Inbound | `POST /stripe-webhook` | Stripe |
| Outbound | Payment webhook Bearer+HMAC | Odoo |
| Outbound | Catalog `ODOO_CATALOG_*` | Odoo Connector |

---

## 4. Modelos / tablas

| Tabla | Rol |
|-------|-----|
| `integration_api_key` | Key: org, name, prefix, hash, status, last_used |
| `integration_api_access_log` | Consumo por endpoint |
| `commercial_bridge_idempotency` | bootstrap/checkout (~7d TTL) |
| `landing_public_idempotency` / `landing_api_rate_bucket` | Landing |

**Ausente vs ADR-037:** Integration entity · `environment` · `scopes` · dual-key `retiring` · `health_state` · `credential_ref`.

Formato key: `enk_` + token; prefix = primeros 12 chars. View-once en UI al crear/regenerar.

---

## 5. Env / secretos (nombres; sin valores)

| Var | Rol |
|-----|-----|
| `MEMBER_LOOKUP_API_KEY` / `MEMBER_LOOKUP_ORG_ID` | Fallback legado + bootstrap DB |
| `PUBLIC_LANDING_API_KEY` / `PUBLIC_LANDING_ORG_ID` | Landing (sistema aparte) |
| `NODEONE_ETS_PROVIDER_ORG_ID` | Provider org commercial bridge |
| `ODOO_*` / `STRIPE_*` / `YAPPY_*` / `PAYPAL_*` | Outbound / PSP |

**Docs consumidor (no en código EN1):** `EN1_M2M_TOKEN` (DEV tribal) · `credential_ref` (objetivo F2).

Permiso UI: `integrations.manage` (API Manager).

---

## 6. API Center hoy vs ADR-037

| Capacidad | Hoy | Target ADR-037 |
|-----------|-----|----------------|
| CRUD keys + view-once raw | Sí | Mantener |
| Access log | Sí | + filtro por Integration |
| Catálogo / Explorer | Solo membership | + commercial + probe |
| Entidad Integration | **No** | F1 |
| Health CONNECTED/DEGRADED/DISCONNECTED | **No** | F1 |
| Dual-key rotación | **No** (regen mata A) | F3 |
| `credential_ref` / vault handoff | **No** | F2 ESB + emit EN1 |
| Bind env (dev key ≠ prod host) | **No** | §9 |

UI: `/admin/api-center` · nav Sistema → API Center.

CLI: `backend/tools/create_integration_api_key.py`.

---

## 7. Matriz Current → Target (ADR-037)

| Componente | Actual | Target | Acción |
|------------|--------|--------|--------|
| `integration_api_key` | Flat por org | Bajo Integration + env + scopes | **FORMALIZE** F1 |
| Commercial bridge | Live, fuera catalog | Catalog + health probe | **FORMALIZE** F1 |
| Membership verify | Catalog + explorer | Mantener + scopes | **KEEP** |
| `MEMBER_LOOKUP_API_KEY` fallback | Bypass DB | Deprecar | **DEPRECATE** |
| Landing API key | Env separado | Fuera Integration Center salvo GO | **KEEP** / isolate |
| EP1 Device Bearer | Product auth | Fuera ADR-037 M2M | **KEEP** (otro dominio) |
| `EN1_M2M_TOKEN` / scp | DEV ops | `credential_ref` | **REPLACE** F2 |
| Dual-key | No | Overlap retiring | **ADD** F3 |

---

## 8. Riesgos

1. Sin Integration model → no bind producto/env/scopes.  
2. Sin `environment` en key → riesgo reuso cross-silo si se copia hash.  
3. Commercial invisible en API Center.  
4. Regen = corte (no dual-key).  
5. Entrega tribal DEV (`scp` / path) inaceptable en PROD.  
6. Tres mundos de secrets (integration / landing / device) — no mezclar en F1.  
7. Fallback env key (`id≈0`) débil en auditoría.  
8. Una key puede llamar membership **y** commercial (sin scopes).  
9. PROD commercial M2M bloqueado hasta F1–F3.  
10. SPAGHETTI ACCEPT pendiente; impl F1 requiere GO explícito.

---

## 9. Anclas de código

| Área | Path |
|------|------|
| Keys | `backend/nodeone/services/integration_api_keys.py` |
| Models | `backend/models/integration_api.py` |
| Commercial | `backend/nodeone/modules/commercial_bridge/` |
| Membership | `backend/nodeone/modules/membership_verification/` |
| API Center | `backend/nodeone/modules/api_center/` |
| ADR | `docs/ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md` |

---

## 10. STOP / siguientes gates

| Gate | Estado |
|------|--------|
| Inventario M2M (este doc) | **DONE** |
| ACCEPT SPAGHETTI ADR-037 | Pendiente |
| **GO ADR-037 F1** (Integration entity + health + catalog commercial) | OFF |
| F2 credential_ref / ESB vault | OFF |
| F3 dual-key | OFF |
| PROD M2M commercial | **BLOQUEADO** |

**No** iniciar F1–F3 ni tocar PRD hasta GO explícito.
