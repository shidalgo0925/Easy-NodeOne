# EIS-005 — Authentication

| Campo | Valor |
|-------|--------|
| ID | **EIS-005** |
| Versión | **1.0.0** |
| Padre | EIS-000 |
| Estado | **Frozen / Approved** |

---

## 1. Propósito

Definir identidad, confianza y autorización entre EasyAI Core y Connectors de producto.

---

## 2. Actores

| Actor | Rol |
|-------|-----|
| **EasyAI Core** | Caller de Tools / lector de Contexts / consumidor de Events |
| **Connector** | Callee en el producto |
| **Usuario final** | Sujeto opcional en cuyo nombre actúa EasyAI |
| **Service principal** | EasyAI sin usuario (jobs, digest) |

---

## 3. Identidad

Toda request autenticada transporta claims lógicos:

| Claim | Descripción |
|-------|-------------|
| `iss` | Emisor (EasyAI o Product STS) |
| `sub` | Subject (user id o service id) |
| `tenant_id` / `organization_id` | Tenant obligatorio en ops de negocio |
| `product_code` | Producto ETS de la superficie (si aplica) |
| `scopes` | Lista de scopes |
| `act` | Optional: usuario original si hay delegation |

Naming: productos pueden usar `organization_id` (EN1) u `tenant_id` (ARP); Manifest declara el alias (`tenant_claim`).

---

## 4. Trust

1. EasyAI y cada producto establecen **trust** por ambiente (cert/JWKS o secret rotativo).
2. No se comparten DB credentials como “auth EasyAI”.
3. Webhooks de eventos: firma HMAC o JWT (`X-EIS-Signature` conceptual).

---

## 5. Tokens

| Tipo | Uso |
|------|-----|
| **Access token** (Bearer JWT o opaco) | invoke Tool / get Context |
| **Service token** | EasyAI service principal |
| **User-delegated token** | Actuación en nombre de usuario (on-behalf-of) |

S1 no elige vendor OAuth; exige que el Manifest declare `auth_methods[]`: `bearer_jwt` | `bearer_opaque` | `mtls` | `hmac_webhook`.

---

## 6. Firmas

- Requests mutantes: recomendado `Idempotency-Key` + token.
- Webhooks: cuerpo firmado; timestamp anti-replay (ventana p.ej. 5 min).

---

## 7. Scopes

Formato:

```text
eis:{capability}:{access}
```

Ejemplos:

- `eis:commerce.read:invoke`
- `eis:commerce.write:invoke`
- `eis:membership.verify:invoke`
- `eis:events.commerce:subscribe`

El Capability Catalog define el segmento `{capability}`.

---

## 8. Tenant · Organización · Usuario

| Nivel | Regla |
|-------|-------|
| Tenant/Org | Obligatorio en Tools de negocio; cross-tenant solo con scope `eis:platform.admin:*` (futuro) |
| Usuario | Requerido si Tool `permissions` lo exigen; opcional en service digest |
| Producto | No sustituye tenant |

---

## 9. Denegación

Sin auth válida → error `unauthorized` (EIS-008).  
Scope insuficiente → `forbidden`.
