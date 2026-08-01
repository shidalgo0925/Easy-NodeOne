# EPosOne ↔ EN1 — Contrato Installation Lifecycle v1.0

| Campo | Valor |
|-------|--------|
| Estado | **PARCIAL EN1** — bootstrap `installation` + ACK `/installation/ready` (Dev) · gate APK pendiente · **sin** 403 cash/orders |
| Versión | **Installation schema_version = 1** |
| Rector | [`ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md`](ADR-021-EPOSONE-INSTALLATION-LIFECYCLE.md) |
| Precondiciones | EN1-02 (register) · Hito 2 (bootstrap) · License Engine V1 |
| Ámbito | Modo **integrado** únicamente |
| Standalone | **Fuera de alcance** |
| Wire EN1 (esta entrega) | `installation` en bootstrap · hints register · `POST /devices/installation/ready` |
| Fuera de esta entrega | 403 `installation_incomplete` · estados UX APK |

Cambios de wire = **v1.1+** + GO. Este documento fija semántica y forma candidata.

---

## 1. Objetivo

Definir cuándo una instalación integrada pasa a **POS habilitado**, qué debe entregar EN1, qué valida la APK, y qué está prohibido antes de `ready`.

```text
register (EN1-02) → token
       ↓
bootstrap (Hito 2)  ← obligatorio
       ↓
chequeos locales (versión, migraciones, license apply)
       ↓
ready → caja / venta / cobro / impresión permitidos
```

---

## 2. Estados (APK — SoT de UX)

| Estado | Significado | Operación POS |
|--------|-------------|----------------|
| `unprovisioned` | Sin Device Token EN1 | No (salvo standalone) |
| `registered` | `POST /devices/register` OK | **No** |
| `bootstrapping` | Bootstrap / migraciones en curso | **No** |
| `ready` | Checklist §4 completa | **Sí** |
| `blocked` | Licencia/versión/política impiden operar | **No** |
| `failed` | Bootstrap o checklist falló; reintentar | **No** |

### Transiciones

```text
unprovisioned --register OK--> registered
registered --bootstrap start--> bootstrapping
bootstrapping --checklist OK--> ready
bootstrapping --error--> failed
failed --retry bootstrap--> bootstrapping
ready --license/version gate--> blocked
blocked --gate cleared + refresh--> ready
```

EN1 **v1 (primera implementación)** no está obligado a persistir estos estados. La APK es dueña del estado local. Un ACK opcional a EN1 (§7) es fase posterior.

---

## 3. Regla de negocio (integrado)

Hasta `ready`, la APK **debe rechazar** (UI + capa de dominio local):

| Acción | Permitido antes de `ready` |
|--------|----------------------------|
| Abrir caja / turno | No |
| Vender / cobrar | No |
| Imprimir ticket de venta | No |
| Llamar cash/orders HTTP “de operación” | No (recomendado; enforcement EN1 = opcional post-GO) |
| Register / config / bootstrap | Sí |
| Pantallas de setup / error / reintento | Sí |

`licensed` (License Engine `status=ACTIVE` o GRACE operable) **no** implica `ready`.

---

## 4. Checklist → `ready`

Todos deben cumplirse (orden sugerido):

| # | Chequeo | Fuente |
|---|---------|--------|
| 1 | Device Token válido | Register EN1-02 |
| 2 | Bootstrap HTTP 200 | `GET /api/v1/devices/bootstrap` |
| 3 | Persistió `config` (destino Caja) | Bootstrap / config |
| 4 | Persistió catálogo usable (o política “vacío permitido” explícita) | Bootstrap `products` |
| 5 | Aplicó bloque `license` sin inventar trial local | License Engine V1 |
| 6 | `app_version` / schema cumplen mínimos si EN1 los envía | Bloque `installation` (§5) |
| 7 | Migraciones locales SQLite OK | APK |
| 8 | Estado local → `ready` | APK |

Fallo en 2–7 → `failed` o `blocked` (si es licencia/versión), nunca `ready`.

---

## 5. Bloque `installation` (bootstrap)

**Aditivo** al JSON de bootstrap. Clientes viejos ignoran el objeto.  
**EN1 Dev:** servido desde `build_installation_block()` en `device_provisioning.py`.

```json
{
  "installation": {
    "schema_version": 1,
    "bootstrap_required": true,
    "channel": "integrated",
    "min_app_version": null,
    "min_bootstrap_schema": 1,
    "capabilities": {
      "cash_shifts": true,
      "orders": true,
      "offline": true
    },
    "sync_policy": {
      "mode": "bootstrap_then_incremental",
      "catalog_full_on_mismatch": true
    },
    "deployment": {
      "environment": "dev",
      "server_time": "2026-08-01T16:00:00Z"
    }
  }
}
```

| Campo | Obligatorio v1 | Notas |
|-------|----------------|--------|
| `schema_version` | Sí | Entero; APK rechaza si no soporta |
| `bootstrap_required` | Sí | En integrado: siempre `true` hasta política futura |
| `channel` | Sí | `integrated` (este contrato) |
| `min_app_version` | No | Env `EPOSONE_MIN_APP_VERSION` o `null` = sin gate |
| `min_bootstrap_schema` | No | Default 1 |
| `capabilities` | No | Hint de features de canal; no sustituye `license.features` |
| `sync_policy` | No | Orquestación sync; detalle fino en ADR-003 / Hito 2 |
| `deployment` | No | `environment` desde `EPOSONE_DEPLOY_ENV` / `EASYNODEONE_DEPLOY_ENV` / `EASYNODEONE_SILO` / `FLASK_ENV`; no gate |

**Register (EN1 Dev):** respuesta aditiva `{ "next": "bootstrap", "bootstrap_required": true }` — no breaking.

---

## 6. Errores (APK / futuros EN1)

| Código (lógico) | Cuándo | Acción APK |
|-----------------|--------|------------|
| `bootstrap_required` | Intento de operar en `registered`/`bootstrapping` | Bloquear UI; ir a bootstrap |
| `bootstrap_failed` | HTTP ≠ 200 o payload inválido | `failed`; reintento |
| `app_version_unsupported` | `min_app_version` no cumplida | `blocked`; pedir update |
| `license_inactive` | License Engine no operable | `blocked` (distinto de install incomplete) |
| `installation_incomplete` | (Futuro EN1) cash/orders sin ready ACK | 403 — solo tras GO enforcement |

Hoy EN1 **no** emite `installation_incomplete` en cash/orders.

---

## 7. ACK observabilidad (C3 — EN1 Dev)

```http
POST /api/v1/devices/installation/ready
Authorization: Bearer <DeviceToken>
Content-Type: application/json
```

Body:

```json
{
  "client_install_id": "optional-stable-id",
  "app_version": "2.1.0",
  "ready_at": "2026-08-01T16:00:00Z",
  "checklist": { "bootstrap": true, "license": true }
}
```

| Campo | Obligatorio | Notas |
|-------|-------------|--------|
| `client_install_id` | No | Id local de instalación |
| `app_version` | No | Actualiza `core_pos_terminal.app_version` |
| `ready_at` | No | ISO-8601; default = now UTC servidor |
| `checklist` | No | Objeto JSON libre; si viene, debe ser object |

Respuesta **200**:

```json
{
  "ok": true,
  "installation_ready_at": "2026-08-01T16:00:00Z",
  "client_install_id": "optional-stable-id",
  "device": { "...": "..." }
}
```

Errores: `unauthorized` 401 · `invalid_ready_at` 400 · `invalid_checklist` 400.

Idempotente. Evento audit: `eposone.installation.ready`.  
Bootstrap expone `installation.ready_acked_at` cuando hay ACK previo.

**No** sustituye el gate local de la APK. EN1 **no** bloquea cash/orders por falta de ACK.

---

## 8. Responsabilidades

| Actor | Debe |
|-------|------|
| **EN1** | Register + bootstrap + license + bloque `installation` + ACK ready (Dev); (futuro) gates 403 |
| **APK integrada** | Estados §2; checklist §4; prohibiciones §3; no inventar licencia |
| **APK standalone** | Ignorar este contrato |
| **BO** | Generar código Caja (EN1-02); no “activar POS” por provisioning solo |

---

## 9. Compatibilidad

| Cambio | Breaking? |
|--------|-----------|
| Solo documentación / gate APK | No |
| Añadir `installation` al bootstrap | No (aditivo) |
| Exigir ACK o 403 en cash/orders | Sí para clientes que no implementen — requiere versión mínima + GO |

---

## 10. Criterio de aceptación del contrato

- [ ] Prog1: OK capas, bloque `installation`, compatibilidad  
- [ ] Prog2: OK estados, checklist, prohibiciones UI/dominio  
- [ ] Acuerdo: implementación = chat/GO aparte; primero gate APK, luego wire EN1  

---

## 11. Relación con docs

| Doc | Rol |
|-----|-----|
| ADR-021 | Decisión arquitectónica |
| **Este archivo** | Contrato funcional / wire candidato |
| EN1-02 | Identidad + token |
| Hito 2 | Snapshot bootstrap |
| License Engine V1 | Bloque `license` |

---

*Propuesto 1 ago 2026 — fase B ADR-021. No implementar sin aceptación + GO.*
