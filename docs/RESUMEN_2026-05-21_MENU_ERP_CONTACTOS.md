# Resumen de trabajo — 21 mayo 2026

**Proyecto:** Easy NodeOne (EN1)  
**Entorno de edición:** `/opt/easynodeone/dev/app` → rama `develop`  
**Servicio dev:** `easynodeone-dev` (puerto 9101)

---

## Objetivo general

Evolucionar el ERP hacia un menú por **flujo de negocio** (estilo Odoo / HubSpot): primero comercial y operativo, después finanzas, y **configuración solo en el engranaje**, no en el sidebar.

**Regla UX acordada:**

- **Sidebar** = trabajar (operación del negocio)
- **Engranaje superior** = configurar (parámetros del sistema)

---

## 1. Módulo Contactos y vínculo comercial/finanzas

*(Ya en `origin/develop`)*

| Commit     | Descripción |
|------------|-------------|
| `3b35327`  | Maestro `en1_contact`, módulo Contactos, menú **Comercial → Contactos** |
| `d5ba227`  | DDL `contact_id` en cotizaciones |
| `054207a`  | DDL columnas legacy en `invoices` |
| `3db84d4`  | DDL antes de KPIs en analítica |

**Entregado:**

- Tabla y modelo `en1_contact` (tipo Odoo `res.partner`), separado de `User`.
- Módulo en `backend/nodeone/modules/contacts/` (admin, API, service, integración facturas).
- Facturas, cotizaciones y FE usan `contact_id` → `en1_contact`.
- Redirect `/admin/terceros` → `/admin/contacts`.
- Activación: `NODEONE_CONTACTS_MODULE_ENABLED=1` + módulo SaaS ON por org.

**Documentación:** `docs/PLAN_MODULO_CONTACTOS_EN1.md`

---

## 2. Reorganización del menú ERP

### Commit en remoto

| Commit     | Descripción |
|------------|-------------|
| `3121bdf`  | Primer corte: separar Configuración vs Operaciones en sidebar |

### Refinamiento local *(pendiente de commit)*

Archivos principales:

- `templates/base.html`
- `templates/partials/erp_app_subnav.html`

### Sidebar — solo operación del negocio

```
Dashboard
Analítica
────────────────
Comercial
  • Contactos
  • CRM
  • Servicios
  • Ventas (cotizaciones)
────────────────
[Educación / Membresías / Eventos — si el módulo está activo]
────────────────
Operaciones
  • Taller
  • Contador
  • CRM
  • Agenda
  • Comunicación
────────────────
Finanzas
  • Facturas
  • Pagos
  • Contabilidad
  • Facturación Electrónica
```

**Decisiones de menú:**

- **Ventas** ya no incluye facturas; estas viven en **Finanzas**.
- **Contactos** antes que CRM en Comercial.
- Orden de dominios: Comercial → Operaciones → Finanzas (contabilidad después del trabajo diario).
- Eliminados bloques duplicados del sidebar (Comunicación, Catálogo, Herramientas, Administración viejos).
- Corregido bug en **Finanzas**: Contabilidad y FE quedaban fuera del bloque por un `{% endif %}` prematuro.

### Engranaje superior — toda la configuración

Tras feedback del analista: **eliminado por completo el bloque “CONFIGURACIÓN” del sidebar vertical**.

Todo queda en el menú del **engranaje** (navbar):

1. Branding  
2. Email / SMTP  
3. Multimedia  
4. IA  
5. Guía de productos  
6. Impuestos  
7. Proveedor FE  
8. Usuarios  
9. Organizaciones  
10. Tipos de cita  
11. Reglas de comunicación  
12. CRM Config  

Los ajustes operativos de módulo (p. ej. SLA taller, parámetros contador) permanecen accesibles **dentro de cada módulo** vía subnav horizontal, no en el sidebar lateral.

### Subnav horizontal (`erp_app_subnav.html`)

- **Ventas** → solo cotizaciones.
- **Facturas** → subnav propio bajo Finanzas.
- **Configuración** → subnav contextual al entrar a pantallas de ajustes (no duplica el sidebar).
- Zona CRM operativa separada de pantallas de config.

---

## 3. Correcciones operativas en dev

| Error | Causa | Fix |
|-------|--------|-----|
| 500 listado cotizaciones | `quotations.contact_id` no existía en PG | DDL + `ensure_contacts_schema` en sales |
| 500 `/admin/analytics` | Columnas faltantes en `invoices` | DDL + `invoices_schema.py` + `ensure_analytics_schema()` |
| Bootstrap DDL fallaba | Tablas owned by `postgres` | `ALTER TABLE … OWNER TO enode_dev_user` |

---

## 4. Estado del repositorio (fin de jornada)

### En `origin/develop` (pusheado)

Hasta commit `3121bdf`.

### Pendiente de commit

- ~660 líneas netas en `templates/base.html` y `templates/partials/erp_app_subnav.html` (menú final + config solo en engranaje).

### WIP local — no commitear como maestro canónico

- `backend/nodeone/modules/commercial_partners/`
- `commercial_partner_schema.py`, templates `terceros_*`
- Cambios WIP en `backend/models/academic.py`

**Decisión acordada:** maestro canónico de terceros = **`en1_contact`**, no `tenant_crm_contact`.

---

## 5. Próximo paso recomendado

1. Commit en `develop`, p. ej. `refactor(menu): sidebar operativo y configuración solo en engranaje`
2. Push a `origin/develop`
3. En staging/prod: `git pull` + DDL si aplica (commits `d5ba227`, `054207a`, `3db84d4`) + reinicio de servicio

---

## Referencias

- `docs/PLAN_MENU_ERP_DOMINIOS_EN1.md`
- `docs/PLAN_MODULO_CONTACTOS_EN1.md`
- `docs/PLAN_MAESTRO_CONTACTOS_FACTURACION_FE_EN1.md`
