# ADR-037 — Integraciones M2M, Credenciales y Operación

| Campo | Valor |
|-------|--------|
| ID | **ADR-037** |
| Título | Integraciones M2M, Credenciales y Operación |
| Título EN | Integrations M2M, Credentials & Operations |
| Estado | **Propuesto — PUBLISHED FOR ESB REVIEW** — 12 ago 2026 · pendiente aceptación conjunta CODITO + SPAGHETTI |
| Ámbito | EN1 (SoR de credenciales M2M) · productos consumidores (ESecureBroker y futuros) · operación DEV/STG/PROD |
| Autores | CODITO (EN1 / SoR) · SPAGHETTI (ESB / consumidor) |
| Relacionados | [ADR-014](ADR-014-SUBSCRIPTION-REGISTRY.md) · [ADR-016](ADR-016-COMMERCIAL-LICENSING-V2-ENTITLEMENT.md) · [ADR-022](ADR-022-EN1-MULTIPRODUCT-COMMERCIAL-MODEL.md) · [ADR-026](ADR-026-EASY-INTEGRATION-SPECIFICATION-V1.md) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) · commercial bridge ESB (`/api/v1/commercial/*`) |
| Numeración | **No** usar ADR-009: ya es [Caja EN1](ADR-009-EN1-CAJA-CENTRO-COBRO.md). En chats ESB se mencionó «ADR-009 Integration»; el ID canónico es **ADR-037**. |
| Implementación | **Prohibida** hasta aceptación explícita + GO de implementación (este ADR es solo diseño). |

---

## 1. Contexto

### 1.1 Caso real (DEV, ago 2026) — motivación

El E2E comercial **ESB ↔ EN1** cerró en DEV con éxito:

```text
ESB /registro → EN1 bootstrap/checkout/entitlement
  → Customer/Contract · Individual $55 · ESB-DEV-100 · $0
  → Subscription ACTIVE · Entitlement TRUE → ESB /hoy
```

Para desbloquearlo hizo falta:

1. Emitir Integration API Key en EN1 DEV (`esecurebroker-m2m-dev`).
2. Guardar el raw en `/opt/easynodeone/dev/secrets/…` en CODITO.
3. Autorizar SSH temporal CODITO → SPAGHETTI.
4. `scp` artesanal del raw a `/opt/corredores-dev/var/secrets/…`.
5. Que un programador “sepa” rutas, owners, reinicios y permisos.

**Eso cerró DEV.** **No es aceptable en PROD.**

```text
NO ACEPTABLE EN PROD

«el programador sabe que el token
está en /opt/.../secrets/...»
```

### 1.2 Qué ya existe en EN1 (baseline, no reemplazar a ciegas)

| Pieza | Hoy |
|-------|-----|
| **API Center** (`/admin/api-center`) | UI de keys B2B; permiso `API Manager` |
| `integration_api_key` | Hash SHA-256, prefix, status, `last_used_at`, org binding |
| `integration_api_access_log` | Log de consumo por endpoint |
| Header M2M | `X-API-Key` |
| Bridge comercial ESB | `POST/GET /api/v1/commercial/*` autenticado con esa key |
| Raw secret | Visible **una vez** al crear/regenerar en UI; no se re-muestra |

**Huecos:** no hay entidad «Integración» (producto + entorno + salud), no hay health/probe formal, no hay rotación dual-key sin downtime, no hay entrega de secretos a consumidores sin operador humano, no hay estados CONNECTED/DEGRADED/DISCONNECTED, no hay separación operativa DEV/STG/PROD gobernada, dependencia fuerte del conocimiento interno.

### 1.3 Principio de arquitectura (congelado con E2E)

| Rol | Responsabilidad |
|-----|-----------------|
| **EN1** | SoR comercial + **SoR de credenciales M2M** (emisión, hash, rotación, revocación, auditoría, health del emisor) |
| **ESB** | Consumidor: guarda **referencia de credencial** + secreto en vault/secret store del silo; nunca en Flutter / Mobile API / browser |
| **organization_id = 1** (provider ETS) | Identidad del **proveedor** de la key, no de la correduría cliente |
| **customer_id** | Identidad comercial del comprador ESB en EN1 |

---

## 2. Decisión

Se establece un **modelo operativo de Integraciones M2M** con dos caras simétricas:

1. **EN1 — Integration Center** (evolución del API Center actual).
2. **ESB — Integraciones** (pantalla/ops en corredores; consume credenciales EN1, no las emite).

Reglas duras:

1. El **raw secret se muestra como máximo una vez** (creación o rotación) y nunca se re-lee desde EN1.
2. La **configuración de aplicación** referencia un **credential_ref** (id + prefix + environment), **nunca** el secreto.
3. **DEV / STG / PROD** usan credenciales, stores y políticas **separadas**.
4. **Prohibido** en PROD: scp manual, rutas en cabeza de programador, chat con secretos, keys en repositorios Git.
5. Toda acción privilegiada (crear / rotar / revocar / probar) queda en **auditoría**.
6. El producto no se frena en DEV: ADR-037 es **gate de PROD** para M2M; ESB GO puede seguir en DEV con el mecanismo actual **acotado a DEV**.

---

## 3. Modelo de dominio

### 3.1 Integration (EN1)

Registro lógico de un vínculo M2M:

| Campo | Descripción |
|-------|-------------|
| `integration_id` | ID estable |
| `code` | Ej. `esecurebroker_commercial` |
| `display_name` | «ESecureBroker — Commercial Bridge» |
| `consumer_product` | `esecurebroker` (Product Registry) |
| `provider_organization_id` | Org ETS emisora (tip. provider `#1`) |
| `environment` | `dev` \| `staging` \| `prod` |
| `scopes` | Lista de capacidades (ej. `commercial.bootstrap`, `commercial.checkout`, `commercial.entitlement`) |
| `status` | `draft` \| `active` \| `suspended` \| `retired` |
| `health_state` | Ver §5 |
| `last_check_at` / `last_used_at` / `last_error_code` / `last_error_at` | Observabilidad |
| `credential_ids[]` | Keys activas/pendientes de rotación |

### 3.2 Credential (EN1)

Evolución de `integration_api_key`:

| Campo | Descripción |
|-------|-------------|
| `credential_id` | = key id |
| `integration_id` | FK lógica |
| `key_prefix` | Visible (ej. `enk_TFWN…`) |
| `key_hash` | Único; raw nunca persistido |
| `environment` | Debe coincidir con Integration |
| `status` | `active` \| `rotating` \| `retiring` \| `revoked` \| `disabled` |
| `created_at` / `rotated_at` / `revoked_at` / `last_used_at` | Ciclo de vida |
| `created_by_user_id` | Auditoría |

Notas de estado:

- **`rotating` / dual-key:** A y B pueden estar `active` en overlap (§8).
- **`retiring`:** A marcada para baja tras confirmar tráfico en B; ESB ya apunta `credential_ref` a B.
- **`revoked`:** rechazo inmediato en bridge (401); ESB → DISCONNECTED.

### 3.3 Credential reference (consumidor — ESB)

En config de ESB **solo**:

```text
EN1_COMMERCIAL_CREDENTIAL_REF=esecurebroker_commercial:dev:2
EN1_COMMERCIAL_BASE_URL=https://appdev.easynodeone.com
# Secreto: resuelto por secret backend del silo, no por path hardcodeado en código
```

El runtime resuelve el secreto vía **Secret Backend** del entorno (§7), no vía string literal en `.env` versionado ni path mágico en código fuente.

**View-once (norma):** el raw se muestra **como máximo una vez** en Integration Center (crear/rotar). EN1 **no** lo re-display. ESB **no** almacena raw en UI, settings screen, logs ni Mobile API — solo `credential_ref` + secreto en Secret Backend.

---

## 4. Integration Center (EN1) — capacidades

Extiende `/admin/api-center` (no inventar un silo paralelo sin migración).

| Capacidad | Descripción |
|-----------|-------------|
| Listar integraciones | Por entorno; filtro producto |
| Crear integración | Código, producto, scopes, environment |
| Emitir credencial | Genera raw **una vez**; UI modal «copiar ahora»; EN1 no lo re-muestra |
| Rotar | Dual-key (§8) |
| Revocar / disable | Inmediato; falla cerrada en bridge |
| Probar conexión | Acción «Probar» → probe interno (§5) |
| Health | Badge CONNECTED / DEGRADED / DISCONNECTED |
| Auditoría | Quién / qué / cuándo / resultado |
| Access log | Reutilizar `integration_api_access_log` + filtros por integración |

### RBAC (quién administra)

| Rol / permiso | Puede |
|---------------|--------|
| `API Manager` (existente) | Gestionar keys de su org efectiva |
| Superadmin / platform ops | Integraciones cross-org provider ETS |
| Roles de producto ESB en EN1 | **No** emiten keys; solo leen estado si se les concede vista |
| Programador sin permiso | **No** acceso a Integration Center ni a raw |

Detalle fino de roles: alinear con [`docs/RBAC_Y_ROLES.md`](RBAC_Y_ROLES.md) en GO de implementación.

---

## 5. Health y «Probar conexión»

### 5.1 Estados

| Estado | Significado |
|--------|-------------|
| **CONNECTED** | Último probe OK y tráfico reciente sin errores sostenidos |
| **DEGRADED** | Probe OK pero errores 5xx/timeouts recientes o latencia fuera de umbral |
| **DISCONNECTED** | Probe fallido, key revocada, o sin uso + fallos consecutivos |

### 5.2 Probe (EN1 → self / contrato)

Acción admin «Probar conexión» ejecuta un **health check autenticado** del bridge (endpoint dedicado o `GET …/entitlement` con customer de prueba controlado **solo DEV**).

Reglas:

- No usa credenciales de usuario final.
- Registra `last_check_at`, resultado, latencia.
- En PROD el probe no crea customers/subscriptions reales (idempotent read-only o fixture interno).

### 5.3 Si EN1 está caído / degradado (política ESB)

| Situación | Comportamiento ESB |
|-----------|-------------------|
| EN1 unreachable / 5xx | Fail-closed en **onboarding comercial nuevo** (`/registro`, checkout); UX: «servicio comercial no disponible»; **no** inventar `ACTIVE` |
| EN1 OK, entitlement previo cacheado | `/hoy` puede usar **cache con TTL corto** + marcar DEGRADED; no inventar ACTIVE |
| Key revocada (401) / DISCONNECTED | `/hoy` y sync hacia Mobile API: estado no-entitled / degradado según contrato ESB; **fail-closed** comercial |
| Durante `retiring` (rotación) | ESB ya usa ref B; si B falla → DEGRADED/DISCONNECTED; no volver silenciosamente a A si A está `retiring`/`revoked` |
| Mobile / ESB GO | **No** consulta EN1; depende de ESB Mobile API. Si ESB no pudo sincronizar entitlement, GO ve estado degradado según contrato ESB (fuera de alcance de emisión EN1) |

---

## 6. ESB — pantalla Integraciones (lado consumidor)

SPAGHETTI define UI/ops en corredores:

| Capacidad | Descripción |
|-----------|-------------|
| Ver integración EN1 Commercial | `credential_ref`, environment, health (si EN1 lo expone), last_sync |
| Configurar base URL por entorno | appdev / staging / prod |
| Estado secreto | `configured` / `missing` / `stale` — **sin mostrar raw** |
| Probar | Llama health/probe C1 o entitlement smoke controlado (DEV) |
| Rotación recibida | Ops actualiza Secret Backend + `credential_ref`; marca «secreto actualizado» |

### 6.1 Información segura visible en UI (permitido)

| Campo | Visible |
|-------|---------|
| Nombre integración / `code` | Sí |
| `credential_ref` | Sí |
| `key_prefix` | Sí |
| `environment` | Sí |
| `status` / `health_state` | Sí |
| `last_used_at` / `last_check_at` | Sí |
| `last_error_code` + mensaje **seguro** (sin token) | Sí |
| Raw secret / hash completo | **Nunca** |

ESB **nunca**:

- Emite keys EN1.
- Guarda raw en Git, Flutter, Mobile API, browser, logs, pantallas de settings.
- Usa la misma key DEV en PROD (fail-closed si detecta cruce de entorno).

---

## 7. Despliegue de secretos (reemplazo del scp artesanal)

### 7.1 Objetivo

```text
Operador autorizado
  → Integration Center (emit/rotate)
  → raw mostrado 1 vez O escrito a Secret Backend vía canal controlado
  → runtime del consumidor lee por credential_ref
```

### 7.2 Secret Backend por entorno (normativo)

| Entorno | Backend admitido (elegir uno por silo; documentar en ops) |
|---------|----------------------------------------------------------|
| DEV | Secret file **fuera de Git** con ACL, o secret manager local; path **no** hardcodeado en código — solo en unit/env del silo |
| STG / PROD | Secret manager / vault / systemd credentials / cloud secret store |

### 7.3 Prohibiciones

- `scp` entre VPS como procedimiento PROD.
- SSH temporal entre productos como canal de secretos.
- Documentar paths absolutos de secretos en ADRs públicos o chats como «fuente de verdad».
- Commitear `.raw`, `.pem`, tokens.

### 7.4 Procedimiento DEV excepcional (transitorio)

Hasta implementar ADR-037:

- Permitido **solo DEV**, auditable, con auth mínima y retiro de acceso SSH tras handoff.
- Cualquier repetición del patrón CODITO↔SPAGHETTI scp = **deuda explícita**, no plantilla PROD.

---

## 8. Rotación sin downtime (dual-key)

```text
1. EN1: emitir credencial B (status=active) manteniendo A active  → overlap
2. Entregar raw B al Secret Backend del consumidor (view-once)
3. ESB: actualizar credential_ref → B; hot-reload / restart silo
4. EN1 «Probar» con B; access log confirma tráfico B
5. EN1: marcar A = retiring → luego revoke A
6. Auditoría: rotate completed (bind/test/status sin secretos)
```

Ventana dual-key máxima recomendada: configurable (ej. 24–72 h); alerta si A sigue en uso tras grace.  
**Revoke** de A es inmediato en el bridge; reintentos con A → 401.

---

## 9. Separación de entornos

| Regla | Valor |
|-------|--------|
| Key DEV | Solo `environment=dev` + BD/host DEV |
| Key STG | Solo staging |
| Key PROD | Solo prod; emisión requiere rol elevado + justificación auditada |
| Promo `ESB-DEV-100` | Solo BD `easynodeone_dev` (ya enforced) |
| Bridge comercial | Feature/scopes por environment; PROD **no** acepta keys DEV aunque el hash coincida (binding environment) |
| Consumidor ESB | Fail-closed si `credential_ref.environment` ≠ entorno del silo (mismo espíritu que pareo ADR-006 / env pairing) |

---

## 10. Auditoría y observabilidad

Mínimo registrable:

- create / rotate / revoke / disable / enable
- probe result
- auth failures (401) agregados
- `last_used_at` por credencial
- actor (`user_id`), IP admin, timestamp

Retención: según política de logs EN1 (definir en GO implementación; no borrar en este ADR).

---

## 11. Caso ESecureBroker Commercial (instancia de referencia)

| Campo | Valor canónico |
|-------|----------------|
| `integration.code` | `esecurebroker_commercial` |
| Endpoints | `/api/v1/commercial/bootstrap` · `checkout` · `entitlement` |
| Auth | `X-API-Key` |
| Provider org | ETS provider (`NODEONE_ETS_PROVIDER_ORG_ID`) |
| Consumidor | ESB (corredores) — no Flutter, no Mobile API |
| Identidad comercial | `customer_id` (no `external_en1_org_id` como org correduría) |

Lección del E2E: mapear mal `organization_id` del provider a la org operativa ESB rompe el modelo. Queda **norma**:

```text
EN1 provider org ≠ ESB correduría
EN1 customer_id  = ancla comercial del comprador
ESB organization = dominio operativo en corredores
```

---

## 12. Fuera de alcance (este ADR)

- Implementación de UI/API (requiere GO posterior).
- Producer domain / Assigned Portfolio / ESB GO F4.
- ADR-008 F2 RBAC AccessContext (sigue su propio carril).
- Payment ledger / Intent / PSP.
- EIS Connector SDK (ADR-026): norma distinta (IA); no mezclar.

---

## 13. Plan de adopción (post-aceptación) — fases F1–F3 + STG/PROD

| Fase | Entrega | Gate |
|------|---------|------|
| **Aceptación** | CODITO + SPAGHETTI ACCEPT ADR-037 | Documento |
| **F1** | Integration Center EN1: entidad Integration + ligar keys; health CONNECTED/DEGRADED/DISCONNECTED + Probar (DEV) | GO impl DEV |
| **F2** | ESB Integraciones + Secret Backend + **credential_ref** (sin raw en settings); view-once end-to-end DEV | GO ESB |
| **F3** | Dual-key rotation + revoke + auditoría UI (bind/test/status sin secretos) | GO |
| **STG** | Mismos controles en staging | GO |
| **PROD** | M2M comercial PROD | **Bloqueado hasta F1–F3 + E2E certificado con `credential_ref`** (sin raw en settings; sin scp/path tribal) |

**Gate PROD (norma):**

```text
M2M comercial PROD = OFF
hasta:
  F1 + F2 + F3 DONE
  + E2E certificado:
      registro → bootstrap → checkout → entitlement → /hoy
      usando credential_ref (no EN1_M2M_TOKEN path artesanal)
```

**DEV transitorio:** `EN1_M2M_TOKEN` / archivo de silo puede seguir mientras se desarrollan F1–F3 y ESB GO (ADR-008 F2 en paralelo OK).

**Prioridad relativa:**

- ADR-037 **antes de PROD** M2M.
- **No** bloquea continuar ESB GO en DEV (F4/F5 producto).
- ADR-008 F2 AccessContext puede avanzar en paralelo.

---

## 14. Criterios de aceptación del ADR (diseño) — checklist ESB

| # | Tema consumidor ESB | Cubierto |
|---|---------------------|----------|
| 1 | Integration Center EN1 ↔ Integraciones ESB (emisor vs consumidor; bind por ref) | Sí §2–§6 |
| 2 | `credential_ref` (config = ref, no raw) | Sí §3.3 |
| 3 | View-once (nunca re-display; ESB no raw en UI) | Sí §3.3 · §6.1 |
| 4 | DEV/STG/PROD + fail-closed cruce entorno | Sí §9 |
| 5–6 | Health CONNECTED/DEGRADED/DISCONNECTED + Probar | Sí §5 |
| 7 | Auditoría bind/test/status sin secretos | Sí §10 · §8 |
| 8–9 | Dual-key + revoke (+ `retiring`) | Sí §3.2 · §8 |
| 10 | Secret store; sin scp/path como runbook PROD | Sí §7 · §1.1 |
| 11 | Fail-closed comercial (`/registro`/checkout; no inventar ACTIVE) | Sí §5.3 |
| 12–13 | RBAC + UI segura (name, prefix, status, last_*, errores) | Sí §4 · §6.1 |
| 14–15 | Rotación / EN1 down / DISCONNECTED en `/hoy`+mobile | Sí §5.3 · §8 |
| 16 | Anti-patrón 2026-08-12 (scp + paths + conocimiento tribal) | Sí §1.1 · §7.3 |
| Gate | PROD bloqueado hasta F1–F3 + E2E con `credential_ref` | Sí §13 |

- [ ] Aceptación formal SPAGHETTI + CODITO (pendiente review ESB con artefacto local).

---

## 15. Consecuencias

**Positivo:** M2M operable por roles, auditable, separable por entorno; E2E DEV deja de ser plantilla PROD.  
**Negativo:** hay que evolucionar API Center y secret backends; costo de implementación F1–F3.  
**Riesgo si no se acepta:** el éxito del E2E se copia a PROD con SSH/scp y conocimiento tácito.

---

## 16. Cómo obtener este ADR (canal documental — no secrets)

| Canal | Ubicación |
|-------|-----------|
| **Canónico EN1** | Repo `Easy-NodeOne` · rama `develop` · `docs/ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md` |
| **GitHub** | `https://github.com/shidalgo0925/Easy-NodeOne/blob/develop/docs/ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md` |
| **Mirror EasyWiki** | Repo `EasyWiki` · `main` · `00_Gobierno/ADR/ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md` |
| **GitHub wiki** | `https://github.com/shidalgo0925/EasyWiki/blob/main/00_Gobierno/ADR/ADR-037-INTEGRATIONS-M2M-CREDENTIALS-OPERATIONS.md` |

Nota: el vault en host SPAGHETTI puede vivir en `/opt/easynodeone/Easy-Wiki` (guion); en CODITO el clone operativo es `/opt/easynodeone/dev/EasyWiki`. Son el **mismo repo remoto** `EasyWiki` — hacer `git pull origin main`.

Borrador ESB misnumerado (`adr/ADR-009_m2m_credentials_operations.md`): tras ACCEPT, convertir en **pointer a ADR-037** (ADR-009 = solo Caja EN1).

---

## Changelog

| Fecha | Nota |
|-------|------|
| 2026-08-12 | Propuesto tras E2E ESB↔EN1 DEV (C1 + handoff M2M). ID **037** (ADR-009 ya = Caja). |
| 2026-08-12 | Enmienda review ESB: view-once, UI segura, `retiring`, fail-closed `/hoy`+mobile, gate PROD F1–F3 + checklist 1–16, URLs de obtención. |
