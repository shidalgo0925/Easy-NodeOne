# ADR-035 — Activation Model (Licencia → Credencial → transporte)

| Campo | Valor |
|-------|--------|
| ID | **ADR-035** |
| Título | Modelo de activación — Licencia, código de activación, email, vigencia |
| Estado | **ACCEPTED (arquitectura)** |
| Versión | **1.4** |
| Fecha | Agosto 2026 |
| Autor | Arquitectura EN1 / EPosOne · CODITO + contrato LOCAL |
| Pregunta rectora | **¿Cómo activa el usuario Standalone sin conceptos de provisioning?** |
| Complementa | ADR-031 · ADR-032 · ADR-033 · ADR-034 |
| Gate | EN1_COMMERCIAL_IMPLEMENTATION_GATE (**LIBERADO**) |

---

## 0. Enmienda v1.4 (Standalone UX definitiva)

| # | Norma |
|---|--------|
| A | Standalone UX canónica: **correo + código de activación** (6 dígitos). |
| B | Léxico: solo **“Código de activación de EPosOne”**. Nunca “aprovisionamiento / caja / register / bootstrap” en Standalone. |
| C | EP1 pantalla: Correo + Código + ACTIVAR → `POST …/redeem` con `email` + `activation_code` + `device_uuid`. |
| D | Email post-verify: código + CTA **Descargar EPosOne**. |
| E | Reemisión sobre la **misma** licencia/org (reinstalación / otra tablet). No crear otra empresa. |
| F | Provisioning Connected (ADR-034) aislado. |
| G | App Link / deep link / `activation_ref` quedan **secundarios** (no UX principal Standalone). |

---

## 1. Contrato canónico

```text
Licencia válida → código de activación (bound email) → email/web → EP1 (email+código) → redeem → claims
```

---

## 2. Credencial Standalone

| Campo | Valor |
|-------|--------|
| `activation_code` | 6 dígitos numéricos |
| `bound_email` | Email del titular (case-insensitive) |
| TTL | Default **14 días** (7–30) |
| Uso | Default **1** → `consumed` |
| Rate limit | Por email/IP en validate/redeem |

---

## 3. HTTP Standalone (canónico)

```http
POST /api/v1/activation/validate
POST /api/v1/activation/redeem
```

```json
{
  "email": "user@example.com",
  "activation_code": "482731",
  "device_uuid": "<uuid>",
  "product_code": "eposone"
}
```

(`device_uuid` requerido solo en redeem.)

### Errores

| error | HTTP |
|-------|------|
| `activation_credential_missing` | 400 |
| `activation_credential_ambiguous` | 400 |
| `activation_code_invalid` | 401 |
| `activation_code_expired` | 400 |
| `activation_code_used` | 409 |
| `activation_code_revoked` | 403 |
| `email_mismatch` | 403 |
| `license_revoked` / `license_expired` | 403 |
| `product_mismatch` | 400 |

### Claims post-redeem

`modality=standalone` · `implementation_strategy=self_serve` · `provisioning_hint.next=standalone_assistant` → ADR-033.

---

## 4. Reemisión

`POST /api/v1/activation/reissue` (usuario autenticado de la org, o flujo asistido):

- Revoca códigos `active` de la licencia Standalone
- Emite nuevo código 6 dígitos
- Reenvía email
- Misma org/licencia

---

## 5. Precedencia

v1.4 **enmienda** v1.3 para UX Standalone (email+código). Connected sin cambio de alcance.

---

## 6. Estado

**ACCEPTED** — Agosto 2026 · **v1.4**.
