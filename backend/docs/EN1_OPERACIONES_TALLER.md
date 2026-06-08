# EN1 — Manual de operaciones: módulo Taller (`workshop`)

Guía para **administradores de tenant**, **recepción / asesores de taller** y **equipo de plataforma** que despliega o da soporte a Easy NodeOne (EN1).

Referencias técnicas: [EN1_SAAS_GUARDS.md](./EN1_SAAS_GUARDS.md), [EN1_ROUTES.md](./EN1_ROUTES.md), [MANUAL_USUARIO_FINAL_MODULOS.md](../../docs/MANUAL_USUARIO_FINAL_MODULOS.md) (pasos básicos de usuario).

---

## 1. Qué cubre el módulo

| Capacidad | Descripción |
|-----------|-------------|
| **Órdenes de trabajo (OT)** | Recepción de vehículo, líneas de servicio/producto, totales, notas, asesor. |
| **Inspección** | Mapa de zonas del vehículo, puntos de daño, severidad, fotos por punto. |
| **Checklist** | Lista de ítems de recepción/entrega (condición + notas). |
| **Fotos** | Entrada, proceso y salida (`/static/uploads/workshop/{org_id}/`). |
| **SLA por etapa** | Tiempos esperados, semáforo verde/amarillo/rojo, monitor y alertas. |
| **Cotización** | Generación de cotización en **Ventas** desde la OT (requiere módulo `sales`). |

**Código SaaS:** `workshop`  
**Nombre en catálogo:** «Taller + SLA» (no es módulo *core*; hay que activarlo por organización).

---

## 2. Requisitos previos

### 2.1 Habilitación SaaS (por organización)

1. Admin de **plataforma** → **Organizaciones** → **Módulos** (o equivalente en catálogo SaaS).
2. Activar **`workshop`** para la empresa que opera el taller.
3. El usuario de recepción debe tener sesión con **`organization_id`** de esa empresa (selector de empresa si aplica).

Si el módulo está apagado:

- Pantallas `/admin/workshop/*` redirigen al dashboard con mensaje de error.
- API `/api/workshop/*` responde **403** JSON: `Módulo no habilitado` / `module: workshop`.

### 2.2 Módulos relacionados

| Módulo | Obligatorio | Uso |
|--------|-------------|-----|
| **`workshop`** | Sí | Taller completo. |
| **`sales`** | Solo para **crear cotización** desde OT | Endpoint `POST .../create-quotation`. Sin Ventas: OT y SLA siguen; no se genera `Q-xxxx`. |
| **Catálogo `service`** | Recomendado | Búsqueda de productos/servicios en líneas de OT y overrides SLA por servicio. |
| **Usuarios / membresía** | Sí | Cliente = usuario con membresía activa en la org; se pueden crear clientes rápidos vía API. |

### 2.3 Permisos (RBAC)

En la matriz de permisología EN1 el dominio aparece como **`workshop`** (alias `taller`).

- Acceso admin: `@admin_required` (admin plataforma o permisos RBAC de administración tenant).
- Ajustar permisos finos en **Admin → Usuarios / Roles** según política del cliente.

### 2.4 Despliegue (equipo técnico)

Tras actualizar código en staging/prod:

```bash
# En el silo (ej. prod)
export EASYNODEONE_MIGRATE_PROD_CONFIRM=YES   # solo prod
sudo -E bash /opt/easynodeone/scripts/migrate-easynodeone-instance.sh <dev|staging|prod>
sudo systemctl restart easynodeone-<silo>
```

El bootstrap ejecuta DDL idempotente de taller (`ensure_workshop_sla_schema`) y columnas SLA en `workshop_orders`. La primera petición a `/api/workshop` también puede disparar `_ensure_tables()`.

**No editar** archivos en `staging/prod/relatic` a mano; solo `git pull` + migración + reinicio ([REGLAS-DE-TRABAJO.md](../../REGLAS-DE-TRABAJO.md)).

---

## 3. Rutas y pantallas (operación diaria)

### 3.1 Menú ERP (admin tenant)

Área **Taller** (visible si `saas_module_enabled('workshop')`):

| Pantalla | URL | Función |
|----------|-----|---------|
| Listado / monitor | `/admin/workshop/orders` | Tablero de OT, filtros, SLA, KPIs. |
| Nueva orden | `/admin/workshop/orders/new` | Alta de OT (UI SPA sobre API). |
| Detalle orden | `/admin/workshop/orders/<id>` | Edición, inspección, fotos, transiciones. |
| Ajustes SLA | `/admin/workshop/settings` | Parámetros generales del taller. |
| Procesos / etapas | `/admin/workshop/process-config` | Minutos por etapa y por servicio del catálogo. |

La barra horizontal tipo Odoo (subnav) agrupa Órdenes / Configuración dentro del módulo.

### 3.2 API JSON (prefijo `/api/workshop`)

Todas las rutas llevan **guard SaaS** `workshop` y sesión (`@login_required`). Resumen para soporte L2:

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/zones` | Zonas del mapa de inspección. |
| GET/POST | `/customers/search`, `/customers` | Buscar / alta rápida de cliente. |
| GET | `/products/search` | Servicios del catálogo para líneas. |
| GET/POST | `/orders` | Listar (monitor) / crear OT. |
| GET/PATCH | `/orders/<id>` | Detalle / actualizar (estado, líneas, notas…). |
| GET | `/by-quotation/<quotation_id>` | OT vinculada a una cotización (vista Ventas). |
| GET/PATCH | `/orders/<id>/inspection`, `/inspection-points/...` | Inspección y puntos. |
| POST | `/orders/<id>/photos`, `/inspection-points/<id>/photos` | Subir imágenes. |
| POST | `/orders/<id>/create-quotation` | Crear cotización (**requiere `sales`**). |
| GET/PUT | `/orders/<id>/checklist` | Checklist de recepción. |
| GET | `/sla/monitor` | KPIs, heatmap, alertas SLA. |
| GET/PUT | `/process-stages`, PATCH `.../<id>` | Configuración de etapas SLA. |
| GET/PUT/DELETE | `/service-process-config` | SLA por servicio + etapa. |

**Organización:** las consultas filtran por `tenant_data_organization_id()` / scope admin; no mezclar datos entre empresas.

---

## 4. Flujo operativo de una orden

### 4.1 Códigos y estados

- **Código OT:** `WO-0001`, `WO-0002`, … (secuencial por `organization_id`).
- **Estados** (`ORDER_STATUSES`):

| Estado | Significado operativo |
|--------|------------------------|
| `draft` | Borrador / recepción inicial. |
| `inspected` | Inspección registrada. |
| `quoted` | Cotización generada (`quotation_id` obligatorio para avanzar). |
| `approved` | Cliente aprobó (cotización asociada). |
| `in_progress` | Trabajo en taller. |
| `qc` | Control de calidad. |
| `done` | Trabajo terminado, pendiente entrega. |
| `delivered` | Entregado al cliente (cierre operativo). |
| `cancelled` | Cancelada (sin SLA activo). |

### 4.2 Transiciones permitidas (resumen)

```text
draft → inspected | cancelled
inspected → quoted | draft | cancelled | in_progress
quoted → approved | inspected | cancelled
approved → in_progress | quoted | cancelled | done
in_progress → qc | approved | cancelled | done
qc → done | in_progress | cancelled
done → delivered | qc | cancelled
delivered → (fin)
cancelled → draft (reapertura)
```

**Reglas importantes:**

- Pasar a **`quoted`** o **`approved`** exige **`quotation_id`** (crear cotización antes).
- **`delivered`** solo desde **`done`**.
- Cambio de estado inválido → API `transition_not_allowed` / mensaje amigable en UI.

### 4.3 Procedimiento estándar (recepción → entrega)

1. **Nueva OT** (`/admin/workshop/orders/new`):
   - Cliente (usuario de la org; búsqueda o alta rápida).
   - Vehículo (placa, marca, modelo, VIN, kilometraje).
   - Líneas: descripción, cantidad, precio, impuesto.
   - Checklist y notas de recepción.
   - Fotos de **entrada** (opcional al crear; también en detalle).

2. **Inspección** (detalle OT):
   - Completar zonas del body map y severidad.
   - Fotos por punto de inspección si aplica.
   - Avanzar a **`inspected`** cuando corresponda.

3. **Cotización** (si el cliente cotiza por EN1):
   - Confirmar módulo **`sales`** activo.
   - Acción «Crear cotización» → genera `Q-xxxx` en borrador y enlaza `order.quotation_id`.
   - Revisar en **Ventas → Cotizaciones** (`/admin/sales/quotations/<id>`).
   - Tras aprobación comercial, estado OT **`approved`** → **`in_progress`**.

4. **Ejecución y QC:**
   - `in_progress` → fotos de **proceso** si se documenta avance.
   - `qc` → notas QC en cabecera (`qc_notes`).

5. **Cierre:**
   - `done` → validar totales (`total_final`).
   - `delivered` → fotos de **salida** recomendadas.

6. **Cancelación:** solo si el proceso lo permite; SLA queda en gris.

### 4.4 Buenas prácticas (operación)

- Una OT = un vehículo + un cliente correctos (evitar mezclar placas).
- No cerrar en **`delivered`** sin pasar por **`done`**.
- Usar **notas** y checklist para trazabilidad (reclamos, garantías).
- Mantener líneas con **impuesto** coherente con política fiscal del tenant.
- Si no usan cotizaciones EN1, acordar con negocio cómo saltar estados (p. ej. `inspected` → `in_progress` donde la matriz lo permita).

---

## 5. SLA y monitor

### 5.1 Concepto

Cada OT lleva en BD: `sla_stage_started_at`, `sla_expected_minutes`, `sla_paused`, etc. Al cambiar de estado, el sistema registra historial en `workshop_order_process_log`.

**Semáforo en UI/API:**

| Color | Condición (tiempo en etapa vs esperado) |
|-------|----------------------------------------|
| Verde | ≤ 80 % del tiempo esperado |
| Amarillo | 80 % – 100 % |
| Rojo | > 100 % (retraso) |
| Gris | Cancelada o SLA no aplica |

### 5.2 Tiempos por defecto (si no hay fila en BD)

| Etapa (`stage_key`) | Minutos fallback |
|---------------------|------------------|
| draft | 10 |
| inspected | 30 |
| quoted | 120 |
| approved | 120 |
| in_progress | 180 |
| qc | 20 |
| done | 15 |
| delivered | 15 |

### 5.3 Configuración (admin tenant)

1. **`/admin/workshop/process-config`**
   - Editar **etapas**: nombre, orden, minutos esperados, color, activo/inactivo.
   - **Override por servicio**: un servicio del catálogo puede tener minutos distintos por etapa (`workshop_service_process_config`).

2. **`/admin/workshop/settings`**
   - Parámetros generales del taller (según plantilla desplegada).

3. **Monitor** (listado de órdenes + API `GET /api/workshop/sla/monitor`):
   - KPIs: a tiempo, en riesgo, retrasadas, % cumplimiento.
   - Heatmap de cuellos de botella por etapa.
   - Alertas críticas / preventivas.

**Pausa SLA:** campo `sla_paused` en la OT (p. ej. espera de repuesto); el cálculo usa reloj efectivo según implementación en `sla_service`.

### 5.4 Script de reparación (solo soporte avanzado)

Si el historial SLA quedó inconsistente tras migraciones:

```bash
cd /opt/easynodeone/<silo>/app/backend
/opt/easynodeone/<silo>/venv/bin/python3 scripts/repair_workshop_sla_logs.py
```

Ejecutar solo con ventana acordada y backup de BD.

---

## 6. Integración con Ventas y facturación

| Acción | Dónde | Notas |
|--------|-------|-------|
| Crear cotización desde OT | API `create-quotation` / botón en UI | Copia líneas de OT → `Quotation` borrador; número `Q-xxxx`. |
| Ver OT desde cotización | API `by-quotation/<id>` | Vista previa en módulo Ventas. |
| Factura | Módulo contable / ventas | Campo `invoice_id` en OT para enlace futuro; flujo según configuración `sales` / `accounting`. |

Sin **`sales`**: operar OT e inspección con normalidad; cotización externa o manual.

---

## 7. Checklist de puesta en marcha (nuevo tenant taller)

- [ ] Organización creada y usuarios con membresía en esa org.
- [ ] Módulo SaaS **`workshop`** = ON.
- [ ] Módulo **`sales`** = ON si usarán cotizaciones EN1.
- [ ] Catálogo de **servicios** cargado (precios e impuestos).
- [ ] Impuestos por defecto del tenant configurados.
- [ ] Revisar **etapas SLA** en `/admin/workshop/process-config` (ajustar minutos al negocio).
- [ ] Prueba E2E: crear OT → inspección → cotización → aprobar → `in_progress` → `delivered`.
- [ ] Verificar subida de fotos y espacio en disco (`static/uploads/workshop/`).
- [ ] Tras deploy en silo: migración bootstrap OK + `systemctl status` activo.

---

## 8. Incidencias frecuentes y resolución

| Síntoma | Causa probable | Qué hacer |
|---------|----------------|-----------|
| «Módulo Taller no habilitado» | `saas_org_module` off para `workshop` | Activar en Admin → Módulos para la org. |
| 403 `sales_module_required` | Cotización sin Ventas | Activar `sales` o no usar create-quotation. |
| `quotation_required` al cambiar estado | Falta cotización antes de `quoted`/`approved` | Crear cotización o ajustar flujo acordado. |
| `transition_not_allowed` | Salto de estado no válido | Seguir matriz de §4.2. |
| SLA siempre gris en canceladas | Esperado | — |
| 500 en dashboard tras deploy | DDL incompleto (otras tablas) | `migrate-easynodeone-instance.sh` + revisar `app_errors.log`. |
| API taller 500 puntual | Esquema SLA antiguo | Reiniciar servicio; abrir listado OT (dispara `_ensure_tables`). |
| Fotos no se ven | Ruta o permisos static | Verificar archivo bajo `uploads/workshop/{org_id}/`. |
| Cliente no aparece en búsqueda | Sin membresía en org | Dar de alta usuario/membresía o usar POST `/customers`. |

**Logs:** `<silo>/app/instance/app_errors.log` y `journalctl -u easynodeone-<silo>.service`.

---

## 9. Variables de entorno (referencia)

| Variable | Efecto |
|----------|--------|
| `NODEONE_SKIP_WORKSHOP_MODULE=1` | No registra rutas ni API de taller (apagado total en ese proceso). |

El resto de multi-tenant (`NODEONE_SINGLE_TENANT_ONLY`, catálogo SaaS, etc.) aplica según [EN1_ARCHITECTURE.md](./EN1_ARCHITECTURE.md).

---

## 10. Resumen para comunicar al cliente

> **Taller EN1** centraliza la orden de trabajo del vehículo: recepción, inspección con fotos, tiempos por etapa (SLA), y enlace opcional a cotizaciones de Ventas. Se activa por empresa en el panel de módulos; el equipo de recepción trabaja en **Admin → Taller → Órdenes**, y los supervisores revisan retrasos en el monitor SLA y en **Procesos / etapas**.

---

*Documento operativo EN1 — módulo `workshop`. Código fuente: `nodeone/modules/workshop/`.*
