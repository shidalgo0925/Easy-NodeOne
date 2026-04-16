# Plan de migración Relatic: SQLite → PostgreSQL (estricto)

## 1. Objetivo

Pasar al PostgreSQL de Relatic (`easynodeone_relatic`) los datos del backup SQLite  
`/home/dev/relaticpanama_backup_20260415_020621.db`, **después de que los usuarios ya estén migrados**, sin duplicar trabajo ni romper integridad.

## 2. Qué cubre el script oficial (y en qué orden)

Herramienta: `backend/tools/migrate_sqlite_members_events_to_pg.py`

En una **sola transacción** (`--apply`), el orden interno es:

| Orden | Contenido | Notas |
|------|-----------|--------|
| 1 | **Usuarios** (`user`) | Si el email ya existe en PG, **no duplica**: hace mapa `sqlite_id → pg_id` y actualiza datos del usuario no-admin. |
| 2 | **Planes** (`membership_pricing` → `membership_plan`) | Solo inserta slugs que falten para el `organization_id` destino. |
| 3 | **Plantillas** (`email_template`) | Upsert por `(organization_id, template_key)`. |
| 4 | **Descuentos** (`discount`) | Inserta y mapea ids viejos → nuevos para eventos. |
| 5 | **Pagos** (`payment`) | Requiere `user_map`; pagos sin usuario mapeado se omiten (log). |
| 6 | **Suscripciones** (`subscription`) | Depende de `user_map` y `pay_map`. |
| 7 | **Eventos** | `event`, `event_image`, `event_discount`, `event_registration`. |

Al final ajusta **secuencias** PostgreSQL en las tablas tocadas.

**Sin `--apply`:** solo lectura — imprime conteos SQLite vs PG (`print_summary`). **No escribe nada.**

## 3. Guardas de seguridad del script

- **Aborta** `--apply` si en PG ya hay filas en **`payment`** o **`event`** (salvo `--force`).  
  Motivo: evitar duplicar pagos/eventos si se re-ejecuta mal.
- `--force` solo debe usarse con criterio (riesgo de duplicados si ya había datos parciales).

## 4. Qué **no** migra este script (huecos conocidos)

El backup SQLite incluye muchas tablas que **no** entran en `migrate_sqlite_members_events_to_pg.py`, entre otras:

- Citas y agenda: `appointment*`, `appointment_type`, `appointment_slot`, …
- Catálogo: `service`, `service_category`, `service_pricing_rule` (existe otro flujo: `copy_service_catalog_cross_env.py`)
- Carrito / propuestas: `cart`, `cart_item`, `proposal`
- Facturación: `invoice` (y líneas si existieran en otro esquema)
- Beneficios, membresías alternativas: `benefit`, `membership`, `membership_discount`, …
- CRM/comunicación: `conversation`, `message`, `notification*`, …
- **Certificados (plantilla Canva + eventos):** `certificate_templates`, `certificate_events` (el script principal no las migra).
  - Herramienta dedicada: `backend/tools/migrate_sqlite_certificate_templates_to_pg.py` (dry-run sin `--apply`, luego `--apply`).
  - Los **archivos** referenciados en `background_image` / URLs (`static/uploads/certificates/…`) **no** viajan en el `.db`: hay que **copiarlos** al static del servidor Relatic (el script lo recuerda al finalizar).
- Y el resto de tablas listadas en el backup.

**“Todo lo demás”** respecto al script actual = planificar **fases adicionales** (nuevos scripts o ETL por dominio), con el mismo rigor: backup, dry-run, orden de FKs, validación.

## 5. Permisos del backup SQLite

El usuario del servicio (`nodeone`) puede **no** poder leer `/home/dev/…`. Opciones:

- Ejecutar el script como el propietario del `.db` (p. ej. `dev`), o
- `chmod a+r` sobre el backup (solo si la política de seguridad lo permite), o
- Copiar el `.db` a una ruta legible por quien ejecuta la migración.

## 6. Cuándo **no** re-ejecutar `--apply` del script principal

El script **aborta** `--apply` si en PG ya hay filas en **`payment`** o **`event`**, salvo `--force`.

**Snapshot real (solo lectura, abril 2026):** comparando el backup `relaticpanama_backup_20260415_020621.db` con PG Relatic, los conteos de `payment`, `subscription`, `event`, `event_registration`, `discount` y `email_template` ya coincidían; `user` PG tenía un usuario más que filas en el backup (86 vs 85). En esa situación **no** corresponde volver a lanzar `--apply` salvo decisión explícita (p. ej. backup nuevo con datos nuevos, o estrategia con `--force` y revisión de duplicados). El trabajo pendiente pasa a ser **dominios no cubiertos** por el script (ver §4) o **deltas** definidos aparte.

## 7. Checklist previo a escribir en PG

1. [ ] **Ventana acordada** (baja actividad o mantenimiento).
2. [ ] **Backup PostgreSQL** del destino Relatic:
   - `pg_dump` (o política de snapshots del proveedor) **antes** de `--apply`.
3. [ ] **Ruta del SQLite** fija y comprobada (solo lectura en el servidor):
   - `/home/dev/relaticpanama_backup_20260415_020621.db`
4. [ ] **Variables**: `--dotenv /opt/easynodeone/relatic/.env` con `DATABASE_URL` correcto.
5. [ ] **`organization_id` destino** acordado (suele ser `1` para Relatic; confirmar en `saas_organization`).
6. [ ] **Estado actual de PG**:
   - Si **usuarios ya migrados**: el script sigue siendo coherente (mapeo por email).
   - Contar `payment` y `event` en PG: si **ambos están en 0**, el script puede aplicar el resto sin `--force`.
   - Si ya hay pagos o eventos en PG, **no** ejecutar `--apply` sin decisión explícita (vaciar tablas objetivo desde backup restaurado, o `--force` con análisis de duplicados).

## 8. Comandos (patrón)

Desde `backend/` del código desplegado en el servidor (Relatic):

```bash
# Solo lectura: conteos SQLite vs PG
../venv/bin/python3 tools/migrate_sqlite_members_events_to_pg.py \
  --sqlite /home/dev/relaticpanama_backup_20260415_020621.db \
  --dotenv /opt/easynodeone/relatic/.env \
  --organization-id 1

# Escritura (tras pg_dump y checklist)
../venv/bin/python3 tools/migrate_sqlite_members_events_to_pg.py \
  --sqlite /home/dev/relaticpanama_backup_20260415_020621.db \
  --dotenv /opt/easynodeone/relatic/.env \
  --organization-id 1 \
  --apply
```

Ajustar `--organization-id` si el tenant destino no es `1`.

**Plantillas de certificado** (independiente del script principal; se puede ejecutar cuando ya exista PG poblado):

```bash
../venv/bin/python3 tools/migrate_sqlite_certificate_templates_to_pg.py \
  --sqlite /home/dev/relaticpanama_backup_20260415_020621.db \
  --dotenv /opt/easynodeone/relatic/.env \
  --organization-id 1

../venv/bin/python3 tools/migrate_sqlite_certificate_templates_to_pg.py \
  --sqlite /home/dev/relaticpanama_backup_20260415_020621.db \
  --dotenv /opt/easynodeone/relatic/.env \
  --organization-id 1 \
  --apply
```

Luego copiar `static/uploads/certificates/` desde el origen si aplica (ver salida del script).

## 9. Validación posterior

- [ ] Revisar salida del script (mapas de usuarios, skips de payment, “OK” final).
- [ ] Consultas de conteo en PG vs expectativas del backup (pagos, suscripciones, eventos, inscripciones).
- [ ] Login de usuarios de prueba (passwords venían del SQLite en usuarios existentes según lógica del script).
- [ ] Reiniciar servicio si procede: `sudo systemctl restart easynodeone-relatic.service`
- [ ] Prueba funcional: listado de eventos, inscripciones, panel admin.

## 10. Rollback

- Restaurar el **dump de PG** tomado antes de `--apply`.  
- No confiar en “borrar a mano” salvo procedimiento SQL documentado por tabla y FKs.

## 11. Coordinación recomendada

1. Responsable técnico confirma **organization_id** y estado `payment`/`event` en PG.
2. Operador ejecuta **solo** el paso sin `--apply` y adjunta salida.
3. Tras aprobación: **pg_dump** → `--apply` → validación → comunicado de cierre.
4. Migración de **catálogo de servicios** u otros dominios: plan aparte (herramientas específicas o nuevo script).

---

## 12. Log de ejecución (siguientes pasos)

| Fecha | Paso | Resultado |
|-------|------|-----------|
| 2026-04-15 | Catálogo legacy → PG Relatic org `1` | `import_services_sqlite_to_org.py` sobre `relaticpanama_backup_20260415_020621.db`: **35** servicios, **10** reglas de precio, mapa de **14** categorías (reuso/altas según slug/nombre). |
| 2026-04-15 | Agenda legacy → PG Relatic org `1` | `import_appointments_sqlite_to_org.py`: **2** tipos de cita, **5** asesores, **2** vínculos tipo–asesor, **49** slots, **12** citas (mapeo usuarios por email y `service_id` por nombre de servicio). |

**Pendiente** (no cubierto aún): carritos (`cart*`), facturas (`invoice`), CRM/mensajería (`conversation`, `message`, …), y el resto de tablas del backup — requiere diseño por dominio.

---

*Documento alineado al código en `develop` (`backend/tools/migrate_sqlite_members_events_to_pg.py`). Actualizar si el script cambia.*
