# P0 REFACTOR /start — Inventario + entrega CODITO (Standalone ≠ Connected)

| Campo | Valor |
|------
## Enmienda P1 (2026-08-08) — Cliente bajo ETS (sin cascarón)

`/start` ya **no** crea `saas_organization` por comprador. El cliente comercial (`ets_commercial_customer`) vive bajo la compañía productiva ETS (`saas_organization.id=1` o `NODEONE_ETS_PROVIDER_ORG_ID`), con contrato/suscripción/licencia anclados por `customer_id`. El negocio operativo sigue diferido a EP1 (ADR-033).

-|--------|
| Fecha | 2026-08-07 |
| Entorno | Dev EN1 (`develop`) — **sin** cambios LOCAL/APK en esta fase |
| GO | P0 REFACTOR + NUEVO FLUJO STANDALONE |
| Estado | **Auditoría + refactor EN1 aplicado en código**; revisión humana antes de GO LOCAL |

---

## Concepto obligatorio (cerrado)

```text
QR → /start → Cliente ETS → Suscripción Standalone → 7 días gracia
  → código por email → APK → EP1 activa licencia → ADR-033 local (Café Amor, caja, etc.)
```

**Connected** = asesoría + Org operativa EN1 + ADR-034. No pasa por este `/start`.

---

## A) Código incorrecto encontrado (pre-refactor)

| Área | Problema |
|------|----------|
| `complete_start` | Nombraba `SaasOrganization` con **business_name** (Café Amor en EN1) |
| `complete_start` | Forzaba activación Standalone aunque el plan UI fuera Connected (`starter`/`business`) |
| `complete_start` | Llamaba `DeviceProvisioningService.ensure_provisioning_code` → `legacy_provisioning_code` |
| `_enable_eposone_module` | Habilitaba módulo EPosOne ops en el tenant recién creado |
| `recommend` / default `plan_code=starter` | Empujaba SKU Connected en puerta Standalone |
| Plan `standalone.trial_days=0` | No había gracia de 7 días |
| Léxico | `provisioning_hint` / App Link como si fueran provisioning de caja |
| ADR-031 §18 / ADR-033 | Premisa “Standalone crea Organización = empresa del cliente” mezclada con negocio operativo |

**No se hallaron** rutas `/platform/activate` ni `/platform/connect` en este repo.

---

## B) Qué se eliminó / desactivó en este P0

| Cambio | Detalle |
|--------|---------|
| Nombre Org = negocio | **Eliminado.** Org cascarón: `Cliente EPosOne — {persona}` |
| Provisioning en `/start` | **Eliminado.** `legacy_provisioning_code` siempre `null`; stub sin `DeviceProvisioningService` |
| Habilitar módulo eposone ops | **Desactivado** en `/start` Standalone |
| Plan libre Connected en `/start` | **Forzado** `plan_code=standalone` (ignora `starter`/`business` del body) |
| Mezcla modality | Contrato/activación siempre `standalone` en este flujo |

---

## C) Qué se conserva solo para Connected

| Pieza | Ubicación |
|-------|-----------|
| Register / Bootstrap / codes de caja | `device_provisioning.py`, `devices_v1_routes.py` |
| Bridge activation→provisioning (rechaza standalone) | `_bridge_activation_token` |
| Onboarding B/C/D | `onboarding_v1_routes.py`, `onboarding_auth_service.py` |
| Planes `starter`/`business`/`enterprise` + trial 15 | `commercial_plans.py` |
| Licencias de caja / grace offline | `register_license_service.py` |
| App Link / `activation_ref` / QR técnico | Secundarios ADR-035; no UX principal Standalone |

---

## D) Modelo final — Cliente ETS + suscripción/licencia Standalone

1. **Cascarón comercial EN1** (`saas_organization`): identidad de *cliente de software*, **no** el restaurante. Nombre ≠ Café Amor.
2. **User** owner del cascarón + membership.
3. **`ets_commercial_customer`** + **`ets_commercial_contract`** (`plan=standalone`, `modality=standalone`).
4. **`ets_product_subscription`** en **trial 7 días** + entitlement.
5. **`ets_activation_license`** Standalone (`ends_at` = fin gracia) + **`ets_activation_token`** código 6 dígitos bound al email.
6. Email verify → email “Tu EPosOne está listo” (código + APK).
7. **EP1** crea Café Amor / caja / cajeros localmente (ADR-033).

> Nota P0: el cascarón sigue siendo una fila `saas_organization` (FK actuales del dominio comercial). **No** es Organización operativa ni árbol Sucursal/POS/Caja. Fase posterior posible: Cliente 100 % bajo org ETS (`id=1`) sin cascarón por comprador (requiere DDL).

---

## E) Código de activación

| Campo | Valor |
|-------|--------|
| Formato | 6 dígitos (`100000`–`999999`) |
| Persistencia | `ets_activation_token.token` + `bound_email` + `jti` interno |
| TTL código | **7 días** (alineado a gracia) |
| Uso | `max_uses=1` → `consumed` |
| Reemisión | `POST /api/v1/activation/reissue` — misma licencia/cascarón; revoca códigos `active` previos |
| Email | Tras verify (`deliver_standalone_ready_after_verify` + ready-status) |

---

## F) Contrato HTTP para LOCAL (sin cambio de APK en esta fase)

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

(`device_uuid` solo en redeem.)

**OK redeem (espíritu):**

```json
{
  "ok": true,
  "redeemed": true,
  "modality": "standalone",
  "implementation_strategy": "self_serve",
  "organization_id": <id cascarón comercial>,
  "license_id": <id>,
  "license_expires_at": "<fin gracia/licencia>",
  "provisioning_hint": { "next": "standalone_assistant", "adr": "ADR-033" }
}
```

- `organization_id` = cascarón comercial ETS, **no** implica árbol ops ni Café Amor en EN1.
- **No** usar este código con Register/Bootstrap Connected.
- Errores: `activation_code_*`, `email_mismatch`, `license_*`, etc.

Detalle: [`EPOSONE_EN1_ACTIVATION_HANDOFF_LOCAL_APPDEV.md`](EPOSONE_EN1_ACTIVATION_HANDOFF_LOCAL_APPDEV.md) (actualizar host/commit al cerrar deploy).

---

## G) 7 días y pago/vigencia

| Reloj | Rol |
|-------|-----|
| **7 días** | Trial/gracia comercial Standalone (`trial_days=7` + `license.ends_at` / token TTL) |
| **Post-pago** | Suscripción/licencia ETS (período mensual u otro) — **no** reemitir código cada mes |
| Código | Sirve para **activar instalación**; vigencia continua = licencia, no “código mensual” |

Connected trial 15 días de planes `starter`/`business` **no** aplica a `/start` Standalone.

---

## H) Cambios necesarios en ADR (formalizar)

| ADR | Acción |
|-----|--------|
| **031** | Enmendar §11/§18: Standalone registra **Cliente ETS + cascarón comercial**; el **nombre del negocio operativo** no es Org EN1; nace en EP1 |
| **032** | Reafirmar: implementación Standalone = EP1 local; Connected = árbol EN1 |
| **033** | Camino canónico: activación licencia → asistente local crea negocio; quitar ambigüedad “Org = Café Amor” |
| **034** | Sin cambio de alcance; aislar provisioning de caja **solo** Connected |
| **035** | Ya v1.4 email+código; aclarar: código = **derecho de licencia Standalone**, no Register/Bootstrap; TTL/gracia 7 días |

Gate comercial: actualizar una línea apuntando a esta enmienda P0.

---

## I) Pruebas

- Unit ADR-035 (`test_activation_adr035.py`): email+código / reissue (regresión).
- Manual / E2E pendientes en appdev tras commit: registro `/start` → Org name `Cliente EPosOne — …` ≠ business_name → sin `legacy_provisioning_code` → trial 7 → redeem `modality=standalone`.

---

## Criterio de aceptación (checklist)

- [x] `/start` no nombra Org con Café Amor / business_name  
- [x] No emite provisioning Connected desde `/start`  
- [x] Plan/activación Standalone + 7 días  
- [x] Código email+redeem independiente de Register/Bootstrap  
- [ ] Smoke E2E appdev + commit/push (siguiente paso operativo)  
- [ ] Revisión humana del mapa antes de GO LOCAL  

---

*Entrega CODITO para revisión. No pedir a LOCAL adaptar EP1 hasta GO explícito tras esta revisión.*
