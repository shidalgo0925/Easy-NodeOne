# ADR-035 — Activation Model (Licencia → Token → QR)

| Campo | Valor |
|-------|--------|
| ID | **ADR-035** |
| Título | Modelo de activación — Licencia, Token, transporte, vigencia y seguridad |
| Estado | **ACCEPTED (arquitectura)** — 7 ago 2026 |
| Versión | 1.2 |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne · CODITO + contrato para LOCAL |
| Impacto | EN1 · Portal ETS · EPosOne APK |
| Implementación de código | **Autorizada solo con GO explícito de implementación** |
| Pregunta rectora | **¿Qué es la orden de activación y cómo llega de forma segura al dispositivo?** |
| Complementa | [ADR-032](ADR-032-PRODUCT-IMPLEMENTATION-MODEL.md) · [ADR-031](ADR-031-EN1-COMMERCIAL-DOMAIN-ARCHITECTURE.md) |
| Consumidores | [ADR-033](ADR-033-STANDALONE-ONBOARDING-ASSISTANT.md) · [ADR-034](ADR-034-CONNECTED-PROVISIONING-FLOW.md) |
| Gate | [EN1_COMMERCIAL_IMPLEMENTATION_GATE.md](EN1_COMMERCIAL_IMPLEMENTATION_GATE.md) (**LIBERADO**) |

---

## 1. Contrato canónico

```text
Licencia válida → autorización / Token de activación → transporte → EP1 consume activación
```

```text
Contrato → Suscripción → Licencia (orden) → Token (credencial) → QR|mail|link|copia → EP1
```

---

## 2. Decisiones inequívocas

| # | Norma |
|---|--------|
| 1 | **QR comercial** = embudo `/start` (registro Cliente/Org/Contrato…). **No** activa dispositivos. |
| 2 | **QR técnico** = **solo transporte** del token/credencial de este ADR. **No** es orden comercial; **no** vende; **no** registra clientes. |
| 3 | La **Licencia** es la orden de activación. |
| 4 | El **Token** es la credencial que EP1 canjea (`redeem`). |
| 5 | EP1 conoce la modalidad por claims: `modality` ∈ {`standalone`,`connected`} + `implementation_strategy` ∈ {`self_serve`,`assisted`}. **No pregunta al usuario.** |
| 6 | Standalone: emitir token **sin** árbol ops EN1. Connected: solo si caso `ops_ready` (ADR-034). |

---

## 3. Qué recibe EP1 (claims mínimos post-`redeem`)

| Campo | Uso en EP1 |
|-------|------------|
| `license_id` | Ancla local |
| `organization_id` | Contexto comercial |
| `product_code` | Debe ser `eposone` |
| **`modality`** | `standalone` → ADR-033 · `connected` → ADR-034 |
| **`implementation_strategy`** | `self_serve` \| `assisted` |
| `register_ref` | Requerido típico en Connected; ausente/ignorado en Standalone |
| `license_expires_at` | Vigencia comercial |
| `provisioning_hint` | Connected: siguiente paso register |

---

## 4. Token — TTL, uso, errores, reintentos

| Regla | Valor de arquitectura |
|-------|------------------------|
| TTL token | Independiente de licencia; default propuesto **14 días** (configurable 7–30) |
| Uso | Default **un solo uso** (`max_uses=1`) → `consumed` tras redeem OK |
| Reutilización | Solo si política explícita (`max_uses>1` o re-provision) |
| Expiración | `expires_at` UTC; skew ±5 min |
| Revocación token | `revoked`; no afecta otras licencias |
| Revocación licencia | Invalida **todos** tokens pendientes |
| Reintentos EP1 | Reintentar `validate`/`redeem` ante red; **no** reintentar a ciegas tras `used`/`revoked` |
| Rate limit | EN1 limita intentos por token/IP |

### Errores tipados

| `error` | HTTP | EP1 |
|---------|------|-----|
| `activation_token_invalid` | 400/401 | Mensaje + reingresar |
| `activation_token_expired` | 400 | Pedir nuevo token |
| `activation_token_used` | 409 | Pedir re-emisión / soporte |
| `activation_token_revoked` | 403 | Soporte |
| `license_revoked` / `license_expired` | 403 | Soporte / renovar comercial |
| `ops_not_ready` | 409 | Solo Connected |
| `product_mismatch` | 400 | App incorrecta |
| `modality_mismatch` | 409 | Flujo APK incorrecto |

---

## 5. Licencia (resumen)

Estados: `issued` · `active` · `suspended` · `revoked` · `expired` · `renewed`.  
Campos: producto, modality, strategy, org/contract/subscription, vigencia, firma.

---

## 6. Transporte

QR técnico regenerable desde token `active`. Equivalentes: correo, deep link, copia manual.  
**Nunca** tratar el QR técnico como `/start`.

---

## 7. HTTP (especificación; código = GO aparte)

Emisión admin: `/api/v1/activation/licenses|tokens` (+ `qr.png`).  
Device: `POST /api/v1/activation/validate` · `POST /api/v1/activation/redeem`.  
Luego Connected: `POST /api/v1/devices/register` (token o legacy).

Payloads de ejemplo: sin cambio conceptual respecto v1.1 §11.

---

## 8. Enmiendas / precedencia

| Doc | Efecto |
|-----|--------|
| Pack QR onboarding (`QR_CONTRACT_V1`) | Distinguir **QR comercial** (`/start`) vs **QR técnico** (este ADR). El pack legacy “QR = solo provisioning code” queda **enmendado**: provisioning code es puente; canónico = token. |
| ADR-027 § QR | Misma distinción comercial vs técnico. |
| ADR-021 | Activación previa a register cuando aplique `redeem`. |

---

## 9. Estado

**ACCEPTED (arquitectura)** — 7 ago 2026 · v1.2.  
Código solo con **GO de implementación** explícito.
