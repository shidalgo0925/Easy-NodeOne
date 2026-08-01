# EPosOne ↔ EN1 — Provisioning (contrato oficial EN1-02)

| Campo | Valor |
|-------|--------|
| Hito | **EN1-02 / Hito 1** — Código = destino operativo |
| Estado | **CERRADO / CONGELADO** (13 jul 2026) · E2E tablet Itsmo · tag `eposone-provisioning-v1.0` |
| Commit código | `82c68f7` |
| Handoff | [`EN1_EPOSONE_HANDOFF_STATUS.md`](EN1_EPOSONE_HANDOFF_STATUS.md) |
| Siguiente hito | [`EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md`](EN1_EPOSONE_HITO2_DEVICE_BOOTSTRAP_SYNC_DOWN.md) |
| Reemplaza como contrato oficial | EN1-01 (queda **legacy** / compatibilidad) |

---

## Principio

La complejidad vive en el **BackOffice EN1**.  
El Wizard de la tablet solo pide:

1. URL del servidor  
2. Código de provisioning  

EN1 resuelve Empresa → Sucursal → POS → Caja a partir del código.

---

## BackOffice

1. Crear Sucursal → POS → Caja (register con parent = POS).  
2. EPosOne → **Dispositivos** → **Generar** código para esa Caja.  
3. Entregar el código al instalador.

Tabla: `eposone_provisioning_code` (un código activo por caja; generar rota el anterior).

---

## `POST /api/v1/devices/register`

### Auth

```http
X-EN1-Provisioning-Code: <código de destino>
```

(también body `provisioning_code` o header `X-EPosOne-Provisioning-Code`)

### Body oficial (EN1-02)

```json
{
  "device_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "Tablet Mostrador",
  "platform": "android",
  "device_model": "Sunmi",
  "android_version": "13",
  "app_version": "1.0.0"
}
```

**No** se requieren: `organization_id`, `branch_ref`, `pos_ref`, `register_ref`.

### Respuesta `201`

Igual que EN1-01: `access_token`, `token_type`, `device`, `config` (jerarquía resuelta).

Reprovisionamiento (mismo UUID): reutiliza fila, rota token, bump `config_version`, **201**.

### Errores

```json
{ "error": "provisioning_code_invalid" }
```

---

## `GET /api/v1/devices/config`

```http
Authorization: Bearer <access_token>
```

Sin cambios respecto a EN1-01.

---

## Compatibilidad legacy (EN1-01)

Si el código **no** está en `eposone_provisioning_code` pero el body trae
`organization_id` + `branch_ref` + `pos_ref` + `register_ref` y el código coincide
con el código **por org** (`eposone_settings.provisioning_code`), el registro sigue
funcionando. **No** usar este camino en el Wizard de producto.

---

## curl DEV (contrato oficial)

```bash
curl -sS -X POST 'https://appdev.easynodeone.com/api/v1/devices/register' \
  -H 'Content-Type: application/json' \
  -H 'X-EN1-Provisioning-Code: CODIGO_DE_CAJA' \
  -d '{
    "device_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "device_name": "Tablet Demo",
    "platform": "android",
    "app_version": "1.0.0"
  }'

curl -sS 'https://appdev.easynodeone.com/api/v1/devices/config' \
  -H 'Authorization: Bearer TOKEN'
```

---

## Fuera de alcance

Sync catálogo/ventas · licencias (contrato y serve: Hito 2 / License Engine; este doc no los define) · FE · CRM · IA.

---

## Addendum — Installation Lifecycle (ADR-021)

| Campo | Valor |
|-------|--------|
| Fecha | 1 ago 2026 |
| ADR | [`ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md`](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) |
| Contrato | [`EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md`](EN1_EPOSONE_INSTALLATION_LIFECYCLE_CONTRACT_V1.md) (**propuesto**) |

**Semántica (sin cambio de wire):** EN1-02 solo vincula dispositivo ↔ Caja y emite Device Token. En modo **integrado**, tras `register` la APK **debe** completar el primer `GET /api/v1/devices/bootstrap` con éxito antes de operar (caja, turno, venta, cobro, impresión). Register **no** habilita el POS.

Standalone / wizard local: fuera de alcance de este addendum.
