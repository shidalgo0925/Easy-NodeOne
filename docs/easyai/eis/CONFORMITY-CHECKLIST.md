# Checklist de conformidad — Connector EIS v1.0

| Campo | Valor |
|-------|--------|
| Norma | EIS 1.0.0 Frozen |
| Uso | Obligatorio antes de marcar Connector `ready` |
| Aplica a | EPOSOne, EN1, EM1, ePayroll, EM+Acción, futuros |

Marcar cada ítem: ☐ / ✅ / N/A (justificado).

---

## A. Identidad y Manifest

- [ ] `connector_id` estable y único en Connector Catalog
- [ ] Manifest válido (EIS-006) con `eis_version: "1.0.0"` (o 1.x compatible)
- [ ] `connector_version` SemVer
- [ ] `product.product_code` declarado
- [ ] `lifecycle` coherente con el ambiente
- [ ] `auth.tenant_claim` + `auth_methods` declarados
- [ ] `capabilities[]` ⊆ Capability Catalog (o extensión registrada)
- [ ] `permissions[]` cubre todos los Tools
- [ ] Sin secretos en Manifest

## B. Discovery y Health

- [ ] Manifest alcanzable (well-known o `manifest_url`)
- [ ] Health responde forma EIS-001 §8
- [ ] Discovery no requiere secretos en claro

## C. Contexts (EIS-002)

- [ ] Cada `context_id` documentado / en catálogo o prefijo `x.`
- [ ] Payloads JSON-only (sin ORM/SQL)
- [ ] `schema_version` presente
- [ ] `default_contexts` razonables
- [ ] Tenant reflejado cuando aplica

## D. Tools (EIS-003)

- [ ] Cada Tool tiene `tool_id`, description, schemas in/out
- [ ] `side_effect` correcto (`read`/`write`/`admin`)
- [ ] `capability` alineada
- [ ] AuthZ validada en invoke
- [ ] Audit policy declarada
- [ ] Errores EIS-008
- [ ] No Tool de SQL libre / dump de tabla
- [ ] Writes: idempotencia documentada si aplica

## E. Events (EIS-004)

- [ ] Tipos declarados con `payload_schema`
- [ ] `organization_id` / tenant en eventos de negocio
- [ ] Naming canónico o `event_aliases`
- [ ] Delivery pull/push declarado (aunque implementación sea posterior)

## F. Sessions (EIS-009)

- [ ] Connector no crea `session_id` EasyAI
- [ ] Invoke exige Call Context con tenant
- [ ] No cross-tenant en v1

## G. Security (EIS-011) + Auth (EIS-005)

- [ ] Sin llamadas a LLM desde el Connector / producto por este canal
- [ ] TLS en no-local
- [ ] Scopes `eis:{capability}:…` respetados
- [ ] Webhooks firmados si hay push
- [ ] PII/audit según política

## H. Versionado (EIS-010)

- [ ] Breaking changes → MAJOR de Connector
- [ ] Deprecation con fecha si aplica

## I. Interoperabilidad EasyAI Core

- [ ] Documentado qué Contexts/Tools usará Context Builder / Tool Dispatcher
- [ ] Ningún bypass al AI Gateway
- [ ] Checklist revisado por owner del producto + (opcional) ARP

---

## Resultado

| Campo | Valor |
|-------|--------|
| Connector | |
| Ambiente | |
| Fecha | |
| Revisores | |
| Veredicto | **CONFORME** / **NO CONFORME** |
| Notas | |
