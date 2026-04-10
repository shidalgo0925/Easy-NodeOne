# Imágenes para emails de marketing

Carpeta pública para flyers e imágenes usadas en plantillas de campañas.

## Flyer capacitación Office 365 (Mar 2026)

**Archivo:** `capacitacion-mar26-o365.png`

1. Copia tu imagen (flyer "Primer acceso y uso del correo Microsoft Office 365") en esta carpeta con ese nombre.
2. Ruta completa en el proyecto: `static/public/emails/imagenes/capacitacion-mar26-o365.png`
3. URL pública (al levantar la app):  
   `{{ base_url }}/static/public/emails/imagenes/capacitacion-mar26-o365.png`

## Uso en plantillas de marketing

En el HTML de la plantilla puedes poner:

```html
<img src="{{ base_url }}/static/public/emails/imagenes/capacitacion-mar26-o365.png" alt="Capacitación Office 365" width="600" style="max-width:100%; height:auto;">
```

Al enviar la campaña, `{{ base_url }}` se reemplaza por la URL base del sitio (ej. `https://app.example.com`), así el correo muestra la imagen desde tu servidor.

## Otras imágenes

Puedes añadir más archivos aquí (PNG o JPG) y referenciarlos con:

`{{ base_url }}/static/public/emails/imagenes/NOMBRE_ARCHIVO`
