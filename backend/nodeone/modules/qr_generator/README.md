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

### Fase 6 — Copiar desde historial

- En cada fila PNG/SVG: botón **Copiar** obtiene el archivo vía `GET /api/qr/<id>/download`, actualiza la vista previa (fondo tablero si el registro tenía transparencia, según `GET /api/qr/<id>`) y pega en el portapapeles como en la Fase 5. Los PDF solo tienen **Descargar**.

### Fase 7 — Lote (ZIP)

- `POST /api/qr/batch` — JSON `{ lines: string[], format, size, error_level, style? }` (misma forma que en generate). Respuesta **ZIP** con `qr-001.png` … según formato.
- Hasta **40** líneas no vacías; cada línea se valida como un contenido suelto (`https://` obligatorio para URLs).
- No crea filas en `qr_codes` (solo descarga).
- La UI incluye un bloque plegable **Generación por lotes** que usa los mismos controles de formato/estilo que el formulario principal.

## API

- `POST /api/qr/generate` — respuesta binaria (archivo).
  - **JSON**: `{ content, format, size, error_level, style?: { fill, bg, transparent, border, logo_base64? } }`
  - **`multipart/form-data`**: mismos campos + archivo `logo` (útil cuando hay logo).
- `GET /api/qr/list` — últimos registros (`?q=` filtra por contenido); `has_style` indica si hay `style_json`.
- `GET /api/qr/<id>` — un registro (ver Fase 4).
- `GET /api/qr/<id>/download` — regenera con datos del historial (incl. estilo guardado).
- `POST /api/qr/batch` — varias líneas → ZIP (`qr-001.ext` …); ver Fase 7.
- `DELETE /api/qr/<id>` — borrar historial (misma org).

## UI

- `/admin/tools/qr` y `/tools/qr` (admin autenticado); query `?content=` precarga el campo.
- Botones: Generar, Descargar, **Copiar imagen** (PNG/SVG en vista previa), Copiar contenido (texto del campo).
- Historial: Descargar, **Copiar** (PNG/SVG), Cargar (rellena formulario), Eliminar.
- **Generación por lotes:** textarea multilínea + Descargar ZIP (máx. 40 líneas).
- Enlaces rápidos desde admin: eventos (ficha pública), programas académicos, pagos (carrito), catálogo servicios; texto de ayuda en formatos de certificado.

## Entorno

- `NODEONE_SKIP_QR_GENERATOR_MODULE=1` — no registrar rutas.
