# Fase E — Operación y reintentos

**Dependencias:** Fase A mínimo; ideal con C y D.

## Objetivo

Reintento manual, descarga PDF/XML, consulta por CUFE, reenvío correo (si API lo permite), dashboard fiscal básico.

---

## E.1 Reintento manual

`POST /api/admin/efactura/emissions/<id>/retry`

Condiciones:

- `status in ('error', 'rejected')`
- `retry_count < MAX_RETRIES` (config, ej. 5)
- Regenerar payload desde `electronic_invoice_document` + líneas guardadas (si se modelan líneas en tabla hijo `electronic_invoice_line` — opcional Fase E)

Incrementar `retry_count`; nuevo `event_log` tipo `retry`.

**Sin** reintento automático en cron hasta tener idempotencia PAC confirmada por proveedor.

---

## E.2 Consulta estado

`adapter.query_status(cufe)` → `GET /api/v1/Invoices/{cufe}`

Botón en detalle: “Actualizar estado desde PAC”.

Sincronizar `status` local si cambió.

---

## E.3 PDF / XML

Si emisión guardó base64 en response, persistir en disco/S3 y `pdf_url` / `xml_url`.

Si no, `download_*` del adapter con query `?xml=true` en emisiones futuras.

Admin: botones “Descargar PDF” / “Descargar XML”.

---

## E.4 Dashboard (`/admin/efactura`)

KPIs por org (scope):

- Emitidas hoy / mes
- Aceptadas vs rechazadas vs error
- Último error

Gráfico simple opcional; tabla últimas 10.

---

## E.5 Reenvío correo

Si efacturapty expone endpoint de reenvío (buscar en Swagger `SendInvoiceMail`):

- Botón en detalle
- `event_log` tipo `resend_email`

---

## Aceptación Fase E

- [ ] Reintento tras error simulado recupera emisión
- [ ] Consulta CUFE actualiza estado
- [ ] PDF descargable desde admin
- [ ] Dashboard carga sin cruzar orgs
