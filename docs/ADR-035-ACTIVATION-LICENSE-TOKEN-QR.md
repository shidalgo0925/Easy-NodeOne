# ADR-035 — Activation Model (Licencia → Token → transporte)

| Campo | Valor |
|-------|--------|
| ID | **ADR-035** |
| Título | Modelo de activación — Licencia, credencial, App Link/QR, vigencia y seguridad |
| Estado | **ACCEPTED (arquitectura)** — 7 ago 2026 |
| Versión | **1.3** |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne · CODITO + contrato para LOCAL |
| Impacto | EN1 · Portal ETS · EPosOne APK |
| Implementación de código | Autorizada con GO de implementación (Standalone rediseño appdev) |
| Pregunta rectora | **¿Qué es la orden de activación y cómo llega de forma segura al dispositivo sin que el usuario copie códigos?** |
| Complementa | [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) |
| Consumidores | [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md) · [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md) |
| Gate | [EN1_COMMERCIAL_IMPLEMENTATION_GATE.md](EN1_COMMERCIAL_IMPLEMENTATION_GATE.md) (**LIBERADO**) |

---

## 0. Enmienda v1.3 (Standalone UX)

Esta versión **enmienda** v1.2 en transporte Standalone. No cambia el modelo Licencia → credencial → redeem.

| # | Norma v1.3 |
|---|------------|
| A | Para el usuario Standalone el concepto es solo **Instalar y activar EPosOne**. Provisioning/token/caja/Register/URL EN1 no son UX principal. |
| B | **Transporte #1 (Standalone):** Activation **App Link** HTTPS `…/activate/<activation_ref>`. |
| C | **Transporte #2 (Standalone):** **QR de activación** = la **misma** URL App Link (misma autorización). |
| D | **Fallback:** código alfanumérico `manual_code` solo recuperación / interrupción. Nunca CTA principal. |
| E | Credenciales **tipadas** en HTTP: `activation_ref` **o** `manual_code`. **Prohibido** clasificar por longitud. |
| F | URL/QR llevan solo `activation_ref` opaco de un solo uso (p. ej. `jti`). **No** poner `manual_code` en URL/QR. |
| G | Separación intacta: QR comercial = `/start`; QR activación = transporte técnico. |
| H | Connected/ADR-034 no se desarrolla aquí; camino aislado. |

---

## 1. Contrato canónico

```text
Licencia válida → autorización / credencial → transporte → EP1 consume (redeem)
```

```text
Contrato → Suscripción → Licencia (orden) → Credencial (activation_ref + manual_code)
  → App Link | QR | mail | fallback manual → EP1
```

---

## 2. Decisiones inequívocas

| # | Norma |
|---|--------|
| 1 | **QR comercial** = embudo `/start` (registro Cliente/Org/Contrato…). **No** activa dispositivos. |
| 2 | **QR de activación** = **solo transporte** de `activation_ref` (App Link). **No** es orden comercial. |
| 3 | La **Licencia** es la orden de activación. |
| 4 | La **credencial** que EP1 canjea es `activation_ref` (preferida) o `manual_code` (fallback). |
| 5 | EP1 conoce la modalidad por claims: `modality` ∈ {`standalone`,`connected`} + `implementation_strategy`. **No pregunta al usuario.** |
| 6 | Standalone: emitir sin árbol ops EN1. Connected: solo si `ops_ready` (ADR-034). |

---

## 3. Qué recibe EP1 (claims mínimos post-`redeem`)

| Campo | Uso en EP1 |
|-------|------------|
| `license_id` | Ancla local |
| `organization_id` | Contexto comercial |
| `product_code` | Debe ser `eposone` |
| **`modality`** | `standalone` → ADR-033 · `connected` → ADR-034 |
| **`implementation_strategy`** | `self_serve` \| `assisted` |
| `register_ref` | Connected; ausente/ignorado en Standalone |
| `license_expires_at` | Vigencia comercial |
| `provisioning_hint` | Standalone: `standalone_assistant`; Connected: register |

---

## 4. Credencial — TTL, uso, errores

| Regla | Valor |
|-------|--------|
| TTL | Independiente de licencia; default **14 días** (7–30) |
| Uso | Default **un solo uso** → `consumed` tras redeem OK |
| Reutilización | Solo política explícita / re-emisión |
| Expiración | `expires_at` UTC; skew ±5 min |
| Revocación ref | `revoked`; invalida App Link y `manual_code` de esa fila |
| Revocación licencia | Invalida todos tokens pendientes |
| Rate limit | EN1 limita intentos por ref/IP |

### Errores tipados

| `error` | HTTP | EP1 |
|---------|------|-----|
| `activation_credential_missing` | 400 | Falta credencial tipada |
| `activation_credential_ambiguous` | 400 | Envió `activation_ref` y `manual_code` juntos |
| `activation_token_invalid` | 400/401 | Reingresar / escanear de nuevo |
| `activation_token_expired` | 400 | Pedir re-emisión |
| `activation_token_used` | 409 | Pedir re-emisión / soporte |
| `activation_token_revoked` | 403 | Soporte |
| `license_revoked` / `license_expired` | 403 | Soporte / renovar |
| `ops_not_ready` | 409 | Solo Connected |
| `product_mismatch` | 400 | App incorrecta |
| `modality_mismatch` | 409 | Flujo APK incorrecto |

---

## 5. Transporte Standalone (canónico)

```text
App Link:  https://<host-eposone>/activate/<activation_ref>
Deep link: eposone://activate/<activation_ref>
QR:        encode(App Link)   # misma autorización
Fallback:  manual_code (UI oculta / email pie)
```

- Host conceptual prod: `eposone.easytech.services` (despliegue = GO aparte).
- Host appdev: `eposone-dev.easynodeone.com`.

**Nunca** tratar el QR de activación como `/start`.

---

## 6. HTTP

Emisión: `/api/v1/activation/licenses|tokens` (+ QR App Link).

Device:

```http
POST /api/v1/activation/validate
POST /api/v1/activation/redeem
```

Body tipado (exactamente uno):

```json
{ "activation_ref": "<jti>", "device_uuid": "<uuid>", "product_code": "eposone" }
```

o

```json
{ "manual_code": "XXXX-XXXX-XXXX", "device_uuid": "<uuid>", "product_code": "eposone" }
```

Puente legacy: campo `token` solo → se interpreta como `manual_code` (no por longitud).

---

## 7. Licencia (resumen)

Estados: `issued` · `active` · `suspended` · `revoked` · `expired` · `renewed`.

---

## 8. Enmiendas / precedencia

| Doc | Efecto |
|-----|--------|
| ADR-035 v1.2 | Transporte “token en query” queda **enmendado** para Standalone → App Link path + `activation_ref`. |
| Pack QR onboarding | Comercial `/start` vs activación App Link. |
| ADR-027 / ADR-021 | Misma distinción; redeem antes de register cuando aplique. |

---

## 9. Estado

**ACCEPTED (arquitectura)** — 7 ago 2026 · **v1.3**.
