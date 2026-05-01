# QR Generator (`qr_generator`)

## Alcance

- Multi-tenant: activación vía **Admin → Módulos SaaS** (`qr_generator`).
- QR **estático** (contenido codificado en la imagen).
- Formatos: **PNG**, **SVG**, **PDF**.
- Contenido máximo **2000** caracteres; URLs solo **`https://`**.
- Historial en tabla `qr_codes` (sin QR dinámico ni estadísticas de escaneo).

### Fase 3 — Estilo / marca

- Colores de módulos y fondo (`#RGB` / `#RRGGBB`), fondo **transparente** (PNG; SVG con intento de fondo transparente vía segno).
- **Margen** en módulos de borde (1–10, por defecto 4).
- **Logo** opcional (PNG/JPEG/GIF/WebP, máx. ~250 KB y 512 px de lado): solo **PNG** y **PDF**; la corrección de error sube como mínimo a **Q**.
- El estilo (y el logo en base64) se guarda en **`style_json`** para repetir la misma salida al descargar desde el historial.

### Fase 4 — Reutilizar desde historial

- `GET /api/qr/<id>` — detalle JSON (`content`, formato, tamaño, corrección, `style` con colores/margen/transparencia y `logo_base64` si existía) para alimentar el formulario o integraciones.
- En la UI, **Cargar** en una fila del historial rellena el formulario; si el registro tenía logo, se reutiliza vía `logo_base64` al generar de nuevo sin volver a subir el archivo (mismo criterio que en `POST` JSON).

### Fase 5 — Portapapeles

- En la UI: **Copiar imagen** tras generar: **PNG** → `Clipboard` como imagen (p. ej. para pegar en Canva, Slides, chat); **SVG** → se copia el **texto** del SVG. No aplica a **PDF** (usar Descargar).
- Requiere contexto seguro (**HTTPS** o `localhost`) y un navegador con `navigator.clipboard` / `ClipboardItem` para PNG.

## API

- `POST /api/qr/generate` — respuesta binaria (archivo).
  - **JSON**: `{ content, format, size, error_level, style?: { fill, bg, transparent, border, logo_base64? } }`
  - **`multipart/form-data`**: mismos campos + archivo `logo` (útil cuando hay logo).
- `GET /api/qr/list` — últimos registros (`?q=` filtra por contenido); `has_style` indica si hay `style_json`.
- `GET /api/qr/<id>` — un registro (ver Fase 4).
- `GET /api/qr/<id>/download` — regenera con datos del historial (incl. estilo guardado).
- `DELETE /api/qr/<id>` — borrar historial (misma org).

## UI

- `/admin/tools/qr` y `/tools/qr` (admin autenticado); query `?content=` precarga el campo.
- Botones: Generar, Descargar, **Copiar imagen** (PNG/SVG recién generados), Copiar contenido (texto del campo).
- Enlaces rápidos desde admin: eventos (ficha pública), programas académicos, pagos (carrito), catálogo servicios; texto de ayuda en formatos de certificado.

## Entorno

- `NODEONE_SKIP_QR_GENERATOR_MODULE=1` — no registrar rutas.
