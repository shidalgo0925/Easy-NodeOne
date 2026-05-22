# Especificación para programador Odoo — conector EN1 (Modecosa)

**Versión:** 1.0  
**Fecha:** 2026-05-20  
**Audiencia:** desarrollador del módulo Odoo (ERP Modecosa)  
**Cliente:** EasyNodeOne (EN1) — módulo `security_matrix_manager` y futuras integraciones de lectura  

**Estado:** Fase 1 **implementada** en Modecosa (`en1_connector` 19.0.1.0.0). EN1: `catalog_client.py`, `docs/EN1_ODOO_CATALOG_CONFIG.md`.

---

## 1. Por qué este enfoque

EN1 **no debe** usar XML-RPC con usuario/contraseña de Odoo hacia internet:

- Es lento (muchas llamadas `search_read`).
- La organización lo percibe como “puerta abierta” al ERP.
- Exige credenciales amplias en el servidor EN1.

**Solución acordada:** un **módulo Odoo** (`en1_connector` o nombre similar) que:

1. Lee datos **solo dentro** de Odoo (usuario técnico interno).
2. Los **normaliza** a un JSON estándar (`security_catalog` v1).
3. Los expone por **HTTP(S) con API key de solo lectura** (o entrega un archivo firmado descargable desde Odoo).

EN1 solo consume ese contrato; no conoce modelos internos `ir.*` en crudo.

---

## 2. Integraciones existentes (no cambiar)

| Dirección | Uso actual | Contrato |
|-----------|------------|----------|
| **EN1 → Odoo** | Pagos confirmados (webhook) | JSON + `Authorization: Bearer` + firma HMAC (`odoo_integration_service.py`) |
| Variables EN1 | `ODOO_API_URL`, `ODOO_API_KEY`, `ODOO_HMAC_SECRET`, `ODOO_INTEGRATION_ENABLED` | Ya en producción |

Este documento cubre la integración **Odoo → EN1** (catálogo de seguridad). Son canales distintos.

---

## 3. Alcance por fases

### Fase 1 — Solo lectura (prioridad)

EN1 necesita un **snapshot** para:

- Descargar plantilla XLS de matriz (usuarios y grupos reales de Odoo).
- Validar un XLS subido por el usuario (usuarios/grupos existen, membresías actuales).
- Generar **preview** (grupos a agregar / quitar por usuario).
- Análisis IA (sin ejecutar nada en Odoo).

**El módulo Odoo NO aplica cambios en Fase 1.**

### Fase 2 — Ejecución acotada (después de aprobación en EN1)

Solo cuando EN1 envíe una orden explícita y auditada:

- **Permitido:** agregar o quitar un usuario de un **grupo** (`res.groups` / relación `res.users` ↔ grupos).
- **Prohibido:** modificar `ir.model.access`, `ir.rule`, menús, módulos, usuarios nuevos, contraseñas, ACL técnicas.

Fase 2 se documenta en la sección 8; no implementar hasta que Fase 1 esté en producción.

---

## 4. Módulo Odoo sugerido

| Item | Valor sugerido |
|------|----------------|
| Nombre técnico | `en1_connector` |
| Dependencias | `base` (mínimo); opcional `hr` si exportáis departamento/jefe |
| Usuario interno | Usuario técnico dedicado, ej. `en1_api_reader` — **solo** grupos de lectura necesarios para armar el JSON |
| Configuración | `ir.config_parameter`: URL callback EN1 (opcional), API keys, IP allowlist |

---

## 5. Autenticación y seguridad

### 5.1 API key (obligatorio)

- Header: `Authorization: Bearer <api_key>`
- La key se genera en Odoo (ajustes del módulo); **no** es la contraseña de un usuario humano.
- Rotación: poder revocar y emitir otra sin tocar usuarios reales.

### 5.2 Opcional (recomendado)

- `X-EN1-Request-Id`: UUID por petición (auditoría).
- `X-EN1-Timestamp` + firma HMAC (mismo patrón que el webhook de pagos EN1→Odoo).
- **Allowlist de IP** en nginx/Odoo: solo IPs del VPS EN1 (dev/prod).
- Rate limit: ej. 10 req/min por key para catálogo completo.

### 5.3 Respuestas de error

```json
{
  "ok": false,
  "error": {
    "code": "unauthorized",
    "message": "API key inválida o expirada"
  }
}
```

HTTP: `401` unauthorized, `403` forbidden, `429` rate limit, `500` error interno.

---

## 6. Endpoint principal — catálogo de seguridad (Fase 1)

### `GET /api/en1/v1/security-catalog`

**Headers obligatorios:**

| Header | Valor |
|--------|--------|
| `Authorization` | `Bearer <API_KEY>` |
| `X-Odoo-Database` | `modecosa` (o query `?db=modecosa`) |

**Query opcionales:**

| Parámetro | Descripción |
|-----------|-------------|
| `include` | Lista separada por coma: `users,groups,memberships,model_access,record_rules,modules,menus`. Por defecto: `users,groups,memberships`. |
| `active_users_only` | `true` (default) — solo `res.users` activos |

**Respuesta 200:** cuerpo JSON según esquema **§7**.

**Rendimiento:** una sola respuesta agregada (objetivo &lt; 5 s en bases medianas). Evitar que EN1 haga cientos de llamadas XML-RPC.

**Alternativa aceptable:** exportación manual en Odoo (“Exportar catálogo EN1”) que genera el mismo JSON y lo sube el admin a EN1; el esquema JSON es el mismo.

---

## 7. Esquema JSON estándar `security_catalog` v1

Archivo de referencia: [`schemas/en1_security_catalog_v1.schema.json`](schemas/en1_security_catalog_v1.schema.json)  
Ejemplo: [`schemas/en1_security_catalog_v1.example.json`](schemas/en1_security_catalog_v1.example.json)

### 7.1 Raíz

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `meta` | object | sí | Metadatos del export |
| `users` | array | sí* | Usuarios (*si `include` contiene `users`) |
| `groups` | array | sí* | Grupos de seguridad |
| `memberships` | array | sí* | Relación usuario ↔ grupo (explícita, no solo `group_ids` en user) |
| `model_access` | array | no | ACL resumidas (Fase 1 validación avanzada) |
| `record_rules` | array | no | Reglas de registro resumidas |
| `modules` | array | no | Módulos instalados (referencia) |
| `menus` | array | no | Menús (referencia UI, opcional) |
| `critical_groups` | array | sí | Lista curada de grupos de alto riesgo (ver §7.6) |

### 7.2 `meta`

```json
{
  "schema_version": "1.0",
  "export_type": "security_catalog",
  "generated_at": "2026-05-20T15:00:00Z",
  "database": "modecosa",
  "odoo_version": "19.0+e",
  "exporter": "en1_connector",
  "exporter_version": "1.0.0",
  "record_counts": {
    "users": 42,
    "groups": 111,
    "memberships": 380
  }
}
```

### 7.3 `users[]`

| Campo | Tipo | Obligatorio | Origen Odoo |
|-------|------|-------------|-------------|
| `id` | int | sí | `res.users.id` |
| `login` | string | sí | `login` |
| `name` | string | sí | `name` |
| `active` | bool | sí | `active` |
| `email` | string | no | `email` |
| `share` | bool | no | usuario portal/compartido |
| `department` | string | no | `hr.department` name si existe |
| `parent_login` | string | no | login del jefe (`parent_id`) |
| `group_ids` | int[] | sí | IDs de `groups_id` (redundante con `memberships`, útil para validación rápida) |

**No enviar:** contraseñas, tokens, campos `password`, chatter, archivos.

### 7.4 `groups[]`

| Campo | Tipo | Obligatorio | Origen Odoo |
|-------|------|-------------|-------------|
| `id` | int | sí | `res.groups.id` |
| `name` | string | sí | `name` |
| `category` | string | no | nombre de categoría/privilegio (en Odoo 19 puede no existir `category_id` en `res.groups`; resolver en el módulo) |
| `xml_id` | string | **sí** | ID externo estable, ej. `account.group_account_manager` — **clave para la matriz XLS** |
| `comment` | string | no | descripción |
| `implied_group_ids` | int[] | no | grupos implicados |

EN1 validará filas del Excel contra `xml_id` y `name` (con preferencia por `xml_id`).

### 7.5 `memberships[]`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | int | |
| `group_id` | int | |
| `user_login` | string | denormalizado para depuración |
| `group_xml_id` | string | denormalizado |

Un registro por cada par usuario-grupo **directo** (no expandir grupos implicados salvo flag opcional `expand_implied: true` en query).

### 7.6 `critical_groups[]`

Lista definida en Odoo (datos maestros del módulo), no inventada por EN1. Ejemplo mínimo (ajustar a Modecosa):

| `xml_id` | `risk_level` | `label` |
|----------|--------------|---------|
| `account.group_account_manager` | `critical` | Contabilidad / Manager |
| `stock.group_stock_manager` | `critical` | Inventario / Manager |
| `base.group_system` | `critical` | Administración / Ajustes |
| `base.group_erp_manager` | `critical` | Administrador |

EN1 cruza esto con la hoja **PERMISOS_CRITICOS** del XLS.

### 7.7 `model_access[]` (opcional, `include=model_access`)

| Campo | Tipo |
|-------|------|
| `id` | int |
| `name` | string |
| `model` | string | nombre técnico del modelo, ej. `account.move` |
| `group_id` | int \| null |
| `group_xml_id` | string \| null |
| `perm_read` | bool |
| `perm_write` | bool |
| `perm_create` | bool |
| `perm_unlink` | bool |

### 7.8 `record_rules[]` (opcional)

| Campo | Tipo |
|-------|------|
| `id` | int |
| `name` | string |
| `model` | string |
| `active` | bool |
| `global` | bool |
| `domain_force` | string | dominio Odoo como texto |

### 7.9 `modules[]` / `menus[]` (opcional)

Solo referencia; límite razonable (menús pueden ser miles — enviar `id`, `name`, `parent_id`, `action` opcional).

---

## 8. Fase 2 — Aplicar membresías (futuro)

### `POST /api/en1/v1/security-matrix/apply`

**Headers:** misma API key + rol de escritura separada (`en1_api_executor`) o segunda key.

**Body:**

```json
{
  "meta": {
    "schema_version": "1.0",
    "en1_import_id": "uuid-en1",
    "approved_by": "admin@easytech.services",
    "approved_at": "2026-05-20T16:00:00Z"
  },
  "changes": [
    {
      "action": "add",
      "user_login": "usuario@empresa.com",
      "group_xml_id": "sales.group_sale_salesman"
    },
    {
      "action": "remove",
      "user_login": "usuario@empresa.com",
      "group_xml_id": "account.group_account_invoice"
    }
  ]
}
```

**Respuesta:**

```json
{
  "ok": true,
  "applied": 2,
  "failed": 0,
  "results": [
    {"user_login": "...", "group_xml_id": "...", "action": "add", "status": "ok"},
    {"user_login": "...", "group_xml_id": "...", "action": "remove", "status": "ok"}
  ]
}
```

**Reglas:**

- Rechazar si `user_login` o `group_xml_id` no existe.
- Rechazar `action` distinto de `add` | `remove`.
- Idempotencia: `add` si ya está en el grupo → `ok` sin error; `remove` si no está → `ok`.
- Log en Odoo (`mail.message` o modelo `en1.connector.log`).

EN1 solo llamará esto con import en estado `approved` y sin errores críticos de validación.

---

## 9. Relación con la plantilla XLS de EN1

EN1 usa hojas:

| Hoja | Uso | Datos que deben coincidir con el catálogo Odoo |
|------|-----|-----------------------------------------------|
| `MATRIZ_GENERAL` | Diseño de permisos por área/módulo/pantalla | Referencia a `group_xml_id` |
| `GRUPOS_ODOO` | Catálogo de grupos | `groups[].xml_id`, `name` |
| `USUARIOS` | Usuarios objetivo | `users[].login` |
| `MAPEO_FINAL` | Resultado deseado usuario ↔ grupo | `memberships` vs propuesta |
| `PERMISOS_CRITICOS` | Alertas | `critical_groups` |

**Entregable Odoo útil:** acción “Generar plantilla EN1” que rellene `GRUPOS_ODOO` y `USUARIOS` desde el mismo snapshot (opcional, mismo JSON).

---

## 10. Variables de entorno en EN1 (cuando el módulo exista)

Reemplazan XML-RPC para matriz de seguridad:

```bash
ODOO_CATALOG_URL=https://erp.modecosa.com/api/en1/v1/security-catalog
ODOO_CATALOG_API_KEY=<key solo lectura>
# Opcional: ODOO_CATALOG_HMAC_SECRET=...
```

El script `test_odoo_connection.py` queda como **prueba legacy**; el cliente oficial será `nodeone/integrations/odoo/catalog_client.py` (por implementar en EN1 tras el módulo Odoo).

---

## 11. Checklist de entrega para el programador Odoo

- [ ] Módulo instalable en Odoo 19 (Modecosa).
- [ ] `GET /api/en1/v1/security-catalog` devuelve JSON **§7** válido.
- [ ] API key de lectura; sin XML-RPC público para EN1.
- [ ] `xml_id` en todos los grupos exportados.
- [ ] `critical_groups` configurables en Odoo.
- [ ] Documentar URL y key para el equipo EN1 (canal seguro, no email/chat).
- [ ] Prueba: EN1 puede validar un XLS de prueba sin credencial de usuario humano.
- [ ] (Fase 2) `POST .../security-matrix/apply` con key de ejecución separada.

---

## 12. Contacto / preguntas EN1

| Tema | Responsable EN1 |
|------|-----------------|
| Formato JSON / validación XLS | Backend EN1 — `security_matrix_manager` |
| Webhook pagos (ya existente) | `odoo_integration_service.py` |
| IA y preview | Solo EN1; Odoo no ejecuta IA |

**Próximo paso EN1:** implementar `catalog_client.py` y sincronización en admin cuando Modecosa confirme URL y muestra JSON de prueba.
