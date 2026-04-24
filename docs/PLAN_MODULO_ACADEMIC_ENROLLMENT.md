# Plan: módulo `academic_enrollment` (inscripción dinámica)

**Nombre de módulo (Python / paquete):** `academic_enrollment`  
**Objetivo:** una sola pantalla y un flujo reutilizable para cursos, diplomados, talleres, certificaciones y servicios académicos, con datos en BD, planes de pago, sesión post-login y checkout sin confiar en el landing.

---

## 1. Separación de responsabilidades

| Capa | Rol |
|------|-----|
| **Landing externo (Vite, Webflow, etc.)** | Marketing, CTA, enlaces a `https://<app>/inscripcion/<slug>` (solo slug; **no** precios críticos). |
| **NodeOne (este repo)** | Fuente de verdad: `AcademicProgram`, planes, org, plantilla dinámica, registro/login, carrito, pago, matrícula. |

---

## 2. Modelos (SQLAlchemy)

**Archivo recomendado:** `backend/models/academic_program.py` (nuevo; evitar mezclar con el ERP en `models/academic.py`).

**Coexistencia:** `models/academic.py` ya define `AcademicCourse`, `Enrollment` (ruta Moodle/ERP). El funnel público usa nombres y tablas **propias** para no chocar:

| Modelo | Tabla sugerida | Notas |
|--------|----------------|--------|
| `AcademicProgram` | `academic_program` | Programa ofertable (diplomado, curso, etc.). |
| `AcademicProgramPricingPlan` | `academic_program_pricing_plan` | Planes (full, 6, 10, …). |
| `AcademicProgramEnrollment` | `academic_program_enrollment` | Inscripción del funnel (no confundir con `enrollments` ERP). |

### 2.1 `AcademicProgram`

Campos (alineados al requisito):  
`id`, `organization_id`, `name`, `slug` (único por org), `program_type` (enum: `curso|diplomado|taller|certificacion|servicio|programa`), `category`, `short_description`, `long_description`, `modality`, `duration_text`, `hours`, `language`, `image_url`, `flyer_url`, `price_from`, `currency`, `start_date`, `end_date`, `seats_limit`, `requires_approval`, `status` (p. ej. `draft|published|archived`), `created_at`, `updated_at`.

Índices: `(organization_id, slug)` único; `status`, `organization_id`.

### 2.2 `AcademicProgramPricingPlan`

`id`, `program_id` (FK), `name`, `code` (p. ej. `full`, `6`, `10` — estable para URLs y carrito), `currency`, `total_amount` (Decimal; **mismo criterio que hoy: centavos o unidad mínima** alineado a `resolve_diplomado_plan`), `installment_count`, `installment_amount` (opcional, informativo), `discount_label`, `description`, `is_active`, `sort_order`.

Único sugerido: `(program_id, code)`.

### 2.3 `AcademicProgramEnrollment`

`id`, `organization_id`, `program_id`, `user_id`, `pricing_plan_id`, `status` (`draft|pending_payment|paid|confirmed|cancelled`), `payment_status` (o reutilizar estados de `Payment` vía relación), `created_at`, `confirmed_at`.

Opcional: `partner_id` / `crm_lead_id` (nullable) si se integra CRM después.

**Relación con pago:** `payment_id` o enlace vía metadata del carrito (como hoy `diplomado` en `CartItem.metadata`).

---

## 3. Rutas Flask

**Blueprint:** `academic_enrollment_bp` (o extender `payments_bp` con cuidado — preferible blueprint propio + delegación al carrito existente).

| Método | Ruta | Comportamiento |
|--------|------|----------------|
| GET | `/inscripcion/<program_slug>` | Resuelve programa por `slug` + `organization_id` (tenant); render `program_enrollment.html` o fallback §9. |
| POST | `/inscripcion/<program_slug>/seleccionar-plan` | Valida `plan_code` en BD; guarda en sesión (§6). |
| GET | `/inscripcion/<program_slug>/continuar/<plan_code>` | Login requerido; empuja al carrito (servicio existente `add_*_to_cart`) y `redirect` checkout. |
| GET | `/checkout/programa/<program_slug>/<plan_code>` | Alias o redirect al flujo actual de checkout con ítem ya resuelto (evitar duplicar pasarela). |
| GET | `/inscripcion/gracias/<enrollment_id>` | Confirmación; valida que el usuario sea el dueño o admin. |

**Compatibilidad URL:** Hoy existe `GET /inscripcion/<slug>` y `.../continuar/<plan>` en `_app/modules/payments/routes.py`. Plan: **delegar** en funciones del nuevo módulo con `try BD first, else DIPLOMADOS_IIUS` (§9).

---

## 4. Plantilla única

**Archivo:** `templates/public/program_enrollment.html`

Contexto mínimo: `program` (DTO o modelo), `pricing_plans`, `organization` (branding), `checkout_continuar_url` (generada con `url_for`).

**Reemplazo progresivo** de `inscription_neuro_*.html`: dejan de registrarse en `DIPLOMADO_LANDING_TEMPLATES` cuando exista fila en BD para ese `slug`.

---

## 5. Flujos de usuario

- **Nuevo:** landing → `/inscripcion/<slug>` → elige plan (POST o enlace directo a continuar) → registro → verificar email → `safe_next` a checkout → pago → crear/actualizar `AcademicProgramEnrollment`.
- **Existente:** mismo, con login en lugar de registro.

Reutilizar `safe_next_path` / `oauth_post_login_next` y ampliar con claves §6.

---

## 6. Sesión (contexto post-login)

Claves propuestas (prefijo `enrollment_` o `ae_`):

- `pending_program_slug`
- `pending_plan_code`
- `pending_organization_id`
- `pending_return_url`
- `utm_source`, `utm_campaign` (opcional; query en primera visita)

Tras login/registro exitoso: `redirect` a `pending_return_url` o a `/inscripcion/<slug>/continuar/<plan_code>`.

---

## 7. Integración carrito / facturación

- **Hoy:** `add_diplomado_to_cart` usa `product_type='diplomado'`, precio desde `resolve_diplomado_plan` (servidor).
- **Objetivo:** `add_academic_program_to_cart(user_id, program_id, plan_code)` leyendo **solo BD**; `metadata` incluye `academic_program_id`, `pricing_plan_id`, `enrollment_id` (draft).
- **Product/Service:** opción A) vincular `AcademicProgram` a `Service` (tipo custom); opción B) línea de carrito sin `Service` hasta facturación (como ahora con product_id hash). Documentar decisión en implementación.
- **Nunca** aceptar precio desde el cliente; validar plan activo y monto en servidor.

---

## 8. Administración

Nuevo submódulo bajo admin existente (patrón `admin_*` blueprints):

- CRUD programas (slug, estados, fechas, cupos).
- CRUD planes por programa.
- Lista inscripciones, filtros, export CSV.
- Acciones: publicar, archivar, confirmar matrícula manual.

Permisos: reutilizar `admin_required` / permisos por rol según `nodeone` actual.

---

## 9. Migración desde IIUS (sin romper producción)

Orden:

1. Crear tablas + modelos.
2. Script o admin de **importación** una vez: filas `AcademicProgram` + `AcademicProgramPricingPlan` desde `DIPLOMADOS_IIUS` + textos de plantillas actuales.
3. En `diplomado_landing(slug)`:  
   `if program := AcademicProgram.query.filter_by(slug=slug, organization_id=oid, status='published').first():`  
   `return render_template('public/program_enrollment.html', ...)`  
   `else:` lógica actual (`DIPLOMADO_LANDING_TEMPLATES` + `DIPLOMADOS_IIUS`).
4. Idem para `add_diplomado_to_cart` → primero BD, else diccionario.
5. Cuando migración validada en prod, deprecar plantillas `inscription_neuro_*.html` y diccionario (otro release).

---

## 10. Orden de implementación sugerido (fases)

1. Modelos + migración Alembic/SQL (según estándar del repo).  
2. Servicio de resolución: `get_program_for_enrollment(slug, org_id)` + `resolve_pricing_plan`.  
3. Plantilla `program_enrollment.html` + ruta GET con fallback.  
4. Sesión + ajuste registro/login para `pending_*`.  
5. `add_academic_program_to_cart` + enganche checkout/pago + creación `AcademicProgramEnrollment`.  
6. Admin CRUD.  
7. Script importación desde `DIPLOMADOS_IIUS`.  
8. Limpieza y documentación operativa.

---

## 11. Reglas para el implementador

- **Una plantilla** para todos los programas publicados en BD; el landing solo envía el `slug`.
- **Precios y textos legales** viven en NodeOne (BD), no en el sitio estático.
- **No duplicar** plantillas HTML por diplomado; el histórico queda como fallback temporal (§9).

---

## 12. Referencias en el código actual

- `_app/modules/payments/routes.py` — rutas `/inscripcion/...`
- `_app/modules/payments/service.py` — `DIPLOMADOS_IIUS`, `add_diplomado_to_cart`, `resolve_diplomado_plan`
- `nodeone/core/features.py` — registro de `payments_bp`
- `models/academic.py` — ERP; no mezclar tablas sin diseño explícito
- `templates/public/inscription_*.html` — contenido a migrar a datos + `program_enrollment.html`

---

*Documento vivo: actualizar al cerrar decisiones (Product vs Service, nombres finales de tablas, migraciones).*

---

## Estado de implementación (v1 en código)

- **Modelos** `AcademicProgram`, `AcademicProgramPricingPlan`, `AcademicProgramEnrollment` en `backend/models/academic_program.py` (tablas creadas vía `db.create_all` al arrancar).
- **Servicio** `backend/nodeone/modules/academic_enrollment/service.py` (resolución BD, carrito `academic_program`, post-pago).
- **Rutas** `/inscripcion/<slug>`: prioridad BD → plantilla `public/program_enrollment.html`; si no hay programa publicado, **fallback** `DIPLOMADOS_IIUS` + plantillas legacy.
- **Carrito / API** `add_diplomado_to_cart` y `resolve_product_for_cart` (tipo `diplomado`) intentan BD primero.
- **Post-pago** `process_academic_program_items_after_payment` en `payment_post_process.py`.
- **Alias** `GET /checkout/programa/<slug>/<plan_code>`, **gracias** `GET /inscripcion/gracias/<enrollment_id>`.
- **Admin** mínimo: `GET /admin/academic-enrollment/programs`.
- **Semilla de prueba** `backend/scripts/seed_academic_program_iius_neuro.py` (Neuro-Liderazgo + 3 planes, alineados a IIUS).

Pendiente (siguientes iteraciones): CRUD admin completo, sesión `pending_*` en registro/login, `POST /seleccionar-plan`, tests automáticos, enlace opcional a `Service`/facturación avanzada.
