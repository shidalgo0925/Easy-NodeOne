# Fase 1 - Instrucción Técnica para Cursor/Programador

## Propósito
Implementar el motor contable base de Easy NodeOne sin mezclar módulos financieros posteriores.

## Alcance estricto de la fase
Solo incluye:
- Plan de cuentas
- Diarios
- Asientos contables
- Líneas contables
- Validación de balance
- Publicación
- Reversión

No incluye:
- Facturación automática
- CxC / CxP
- Pagos
- Bancos
- Conciliación
- Impuestos avanzados
- Reportes financieros finales

---

## 1) Diseño de datos

## Tablas mínimas requeridas

### `account`
- `id` PK
- `organization_id` FK `saas_organization.id` (obligatorio)
- `code` varchar(32) (obligatorio)
- `name` varchar(200) (obligatorio)
- `type` enum lógico: `asset|liability|equity|income|expense`
- `is_active` bool default true
- `created_at` datetime
- Unique: `(organization_id, code)`

### `journal`
- `id` PK
- `organization_id` FK
- `name` varchar(120)
- `code` varchar(24)
- `type` enum lógico: `sale|purchase|bank|cash|general`
- `default_account_id` FK nullable `account.id`
- `is_active` bool
- `created_at` datetime
- Unique: `(organization_id, code)`

### `journal_entry`
- `id` PK
- `organization_id` FK
- `journal_id` FK `journal.id`
- `date` date
- `reference` varchar(120) nullable
- `source_model` varchar(80) nullable
- `source_id` int nullable
- `state` enum lógico: `draft|posted|reversed`
- `created_by` FK nullable `user.id`
- `posted_by` FK nullable `user.id`
- `posted_at` datetime nullable
- `reversed_by_entry_id` FK nullable self
- `created_at`, `updated_at`
- Índices por org/fecha/estado/source

### `journal_item`
- `id` PK
- `entry_id` FK `journal_entry.id`
- `account_id` FK `account.id`
- `partner_id` FK nullable `user.id`
- `debit` numeric(14,2) >= 0
- `credit` numeric(14,2) >= 0
- `description` varchar(255) nullable
- Constraints:
  - no ambos lados > 0
  - no ambos lados = 0

---

## 2) Reglas de negocio obligatorias

1. No publicar si `sum(debit) != sum(credit)`.
2. No editar asientos `posted`.
3. Correcciones solo por reversión.
4. Todas las consultas filtradas por `organization_id`.
5. Todo asiento requiere diario válido.
6. Sin montos negativos.
7. Sin débito+crédito en la misma línea.

---

## 3) Servicios backend mínimos

Crear servicio de dominio contable con funciones:

- `ensure_accounting_core_schema()`
- `create_account(org_id, data)`
- `create_journal(org_id, data)`
- `create_entry_draft(org_id, journal_id, payload, user_id=None)`
- `replace_entry_draft_lines(entry, org_id, lines)`
- `validate_entry_for_post(entry)`
- `post_entry(entry, user_id)`
- `reverse_entry(entry, user_id, reverse_date=None)`

Requisitos:
- Manejo de `Decimal` y redondeo a 2 decimales.
- Mensajes de error claros para UI.

---

## 4) Rutas HTTP mínimas (admin)

Prefijo sugerido: `/admin/accounting-core`

- `GET /accounts`
- `POST /accounts`
- `GET /journals`
- `POST /journals`
- `GET /entries`
- `GET /entries/new`
- `POST /entries`
- `GET /entries/<id>`
- `POST /entries/<id>/save-draft`
- `POST /entries/<id>/post`
- `POST /entries/<id>/reverse`

Seguridad:
- `login_required`
- `admin_required`
- scope por organización

---

## 5) UI mínima requerida

Plantillas mínimas:
- `accounting/accounts_list.html`
- `accounting/journals_list.html`
- `accounting/entries_list.html`
- `accounting/entry_form.html`
- `accounting/entry_detail.html`

Acciones obligatorias:
- Crear asiento
- Guardar borrador
- Publicar
- Reversar

Comportamiento:
- Mostrar totales débito/haber en detalle.
- Bloquear edición visual y backend al estar `posted`.

---

## 6) Permisos y modularidad

- Menú Contabilidad separado de Ventas.
- Feature gating por módulo SaaS:
  - `accounting_core` (con fallback de compatibilidad acordado).
- No acoplar lógica contable a facturación en esta fase.

---

## 7) Migraciones y seed

Scripts requeridos:
- migración/creación de tablas del núcleo
- seed inicial mínimo de cuentas y diarios
- importación de plan maestro (si aplica en entorno)

Regla:
- scripts idempotentes (ejecutables varias veces sin duplicar por código).

---

## 8) Pruebas mínimas obligatorias

Cobertura funcional mínima:

1. Crear cuenta válida / rechazar tipo inválido.
2. Crear diario con cuenta por defecto válida.
3. Crear asiento borrador con líneas válidas.
4. Rechazar publicación desbalanceada.
5. Publicar asiento balanceado.
6. Bloquear edición de asiento publicado.
7. Reversar asiento publicado y validar asiento inverso.
8. Aislamiento por organización.

---

## 9) Criterio de aceptación de Fase 1 (Definition of Done)

La fase se acepta solo si:

- Se pueden crear cuentas y diarios por organización.
- Se puede crear asiento manual y guardar borrador.
- Solo se publica si `debe = haber`.
- Se puede reversar asiento publicado.
- No se puede editar asiento publicado.
- Pantallas y rutas mínimas operativas.
- Pruebas verdes para reglas críticas.

Si alguno falla, Fase 1 no está cerrada y no se pasa a Fase 2.
