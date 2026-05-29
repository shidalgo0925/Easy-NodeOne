# Menú lateral EN1 — dominios ERP

Organización del sidebar **tenant admin** por dominios funcionales (estilo ERP / Odoo).

## Mapa completo (Fase 2)

| Dominio | Módulos en menú |
|---------|-----------------|
| **General** | Dashboard, Analítica |
| **Comercial** | CRM, **Contactos**, Servicios, Ventas |
| **Finanzas** | Contabilidad, Pagos, Fact. electrónica |
| **Operaciones** | Taller (órdenes), Contador (inventario y sesiones) |
| **Configuración** | Sitio, impuestos, FE, taller SLA, contador, CRM, agenda, comunicación |
| **Educación** | Programas, Estudiantes, Cursos, Matrículas, Moodle |
| **Eventos** | Ver eventos, Gestión, Descuentos |
| **Membresías** | Beneficios, Gestionar beneficios, Planes / Miembros |
| **Agenda** | Citas, tipos, disponibilidad |
| **Comunicación** | Correo, marketing, chatbots, notificaciones |
| **Catálogo** | Servicios (admin), Categorías, Códigos promo |
| **Herramientas** | Generador QR |
| **Documentos** | Certificados, normativas |
| **Administración** | Matriz permisos, Usuarios, Roles |
| **Plataforma** | Empresas, Módulos SaaS (solo `is_admin`) |

## Principios

1. **Contactos** bajo **Comercial**, no bajo Ventas ni FE (`res.partner`).
2. Títulos de sección: `sidebar-section-title` + separadores `sidebar-menu-divider`.
3. Guards sin cambios: `saas_module_enabled`, `nav_can`, `has_view_endpoint`.
4. Secciones vacías no se muestran (variables `_*_any`).

## Futuro

- Finanzas: Tesorería, Bancos
- Operaciones: Tickets, Proyectos
- Comercial: cotizador dedicado si se separa de Ventas

## Archivos

- `templates/base.html` — sidebar
- `templates/partials/erp_app_subnav.html` — subnav horizontal (Contactos, Eventos, …)
