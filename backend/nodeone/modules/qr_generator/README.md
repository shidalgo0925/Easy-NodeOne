# QR Generator (`qr_generator`)

## Alcance (fase actual)

- Multi-tenant: activación vía **Admin → Módulos SaaS** (`qr_generator`).
- QR **estático** (contenido codificado en la imagen).
- Formatos: **PNG**, **SVG**, **PDF**.
- Contenido máximo **2000** caracteres; URLs solo **`https://`**.
- Historial en tabla `qr_codes` (sin QR dinámico ni estadísticas de escaneo).

## API

- `POST /api/qr/generate` — JSON `{ content, format, size, error_level }` → archivo.
- `GET /api/qr/list` — últimos registros de la organización.
- `DELETE /api/qr/<id>` — borrar historial (misma org).

## UI

- `/admin/tools/qr` y `/tools/qr` (admin autenticado).

## Entorno

- `NODEONE_SKIP_QR_GENERATOR_MODULE=1` — no registrar rutas.
