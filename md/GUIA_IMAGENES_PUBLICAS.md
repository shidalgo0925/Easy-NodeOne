# 📸 Guía de Imágenes Públicas - nodeone

> **IMPORTANTE**: Esta guía explica dónde colocar las imágenes públicas para **emails** y **nuevas funcionalidades**.  
> **NO modificar** las carpetas existentes (`static/images/`, `static/uploads/`).

---

## 📁 Estructura de Carpetas

```
static/
├── public/                    # 🆕 NUEVO - Solo para emails y cosas nuevas
│   ├── emails/                # Imágenes para templates de email
│   │   ├── logos/             # Logos para usar en emails
│   │   └── headers/           # Headers/banners para emails
│   │
│   └── new/                   # Imágenes nuevas que vayamos creando
│       └── (organizar según necesidad)
│
├── images/                    # ✅ NO TOCAR - Ya existe, dejar como está
│   ├── favicon.svg
│   └── logo-primary.svg
│
└── uploads/                   # ✅ NO TOCAR - Archivos subidos por usuarios
    └── events/
```

---

## 🎯 ¿Dónde Colocar Cada Tipo de Imagen?

### 1. **Imágenes para Emails** → `static/public/emails/`

#### Logos para Emails
**Ubicación**: `static/public/emails/logos/`

**Cuándo usar**: Logos que aparecerán en templates de email (bienvenida, confirmaciones, etc.)

**Recomendaciones**:
- ✅ Usar formato **PNG** (mejor compatibilidad con clientes de email)
- ✅ Tamaño recomendado: 90-150px de ancho
- ✅ Optimizar para web (comprimir)
- ✅ Incluir versión blanca si se usa en fondos oscuros

**Ejemplo de archivos**:
```
static/public/emails/logos/
├── logo-primary.png          # Logo principal
├── logo-primary-white.png    # Logo blanco para fondos oscuros
└── favicon.png               # Favicon (si se necesita en email)
```

#### Headers/Banners para Emails
**Ubicación**: `static/public/emails/headers/`

**Cuándo usar**: Imágenes de encabezado o banners para diferentes tipos de emails

**Recomendaciones**:
- ✅ Formato **PNG** o **JPG** (optimizado)
- ✅ Ancho recomendado: 600px (ancho estándar de emails)
- ✅ Alto recomendado: 150-300px
- ✅ Peso máximo: 100KB (para carga rápida)

**Ejemplo de archivos**:
```
static/public/emails/headers/
├── header-bienvenida.png     # Header para email de bienvenida
├── header-congreso.png        # Header para emails de congresos
├── header-taller.png          # Header para emails de talleres
└── header-generic.png         # Header genérico
```

---

### 2. **Imágenes Nuevas** → `static/public/new/`

**Ubicación**: `static/public/new/`

**Cuándo usar**: Cualquier imagen nueva que necesites crear para funcionalidades nuevas

**Organización sugerida**:
- Crear subcarpetas según el propósito
- Ejemplo: `static/public/new/eventos/`, `static/public/new/banners/`, etc.

---

## 💻 Cómo Acceder a las Imágenes

### Para Emails (URLs Absolutas)

Los emails necesitan **URLs absolutas** porque se envían fuera del contexto de la aplicación.

**Usar la función helper**:

```python
from app import get_public_image_url

# En tu código de envío de email
logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
# Retorna: https://app.example.com/static/public/emails/logos/logo-primary.png

header_url = get_public_image_url('emails/headers/header-bienvenida.png', absolute=True)
```

**En templates de email (Jinja2)**:

```html
<!-- En template HTML de email -->
<img src="{{ logo_url }}" alt="Logo Easy NodeOne" style="width: 90px; height: auto;">
```

**Ejemplo completo en Python**:

```python
def send_welcome_email(user):
    # Generar URLs absolutas
    logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
    header_url = get_public_image_url('emails/headers/header-bienvenida.png', absolute=True)
    login_url = f"{request.url_root.rstrip('/')}/login"
    
    # Usar en template
    html = render_template_string(email_template, 
                                   logo_url=logo_url,
                                   header_url=header_url,
                                   login_url=login_url)
    # Enviar email...
```

---

### Para Páginas Web (URLs Relativas)

En templates Jinja2 para páginas web, usar `url_for()`:

```jinja2
{# En templates HTML (páginas web) #}
<img src="{{ url_for('static', filename='public/emails/logos/logo-primary.png') }}" alt="Logo">
```

---

## 🔧 Función Helper

La función `get_public_image_url()` está disponible en `backend/app.py`:

```python
def get_public_image_url(filename, absolute=True):
    """
    Obtener URL de imagen pública
    
    Args:
        filename: Ruta relativa desde static/public/ 
                 (ej: 'emails/logos/logo-primary.png')
        absolute: Si True, retorna URL absoluta (necesario para emails)
                 Si False, retorna URL relativa (para páginas web)
    
    Returns:
        URL completa de la imagen
    """
```

**Ejemplos de uso**:

```python
# Para emails (URL absoluta)
logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
# → https://app.example.com/static/public/emails/logos/logo-primary.png

# Para páginas web (URL relativa)
logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=False)
# → /static/public/emails/logos/logo-primary.png
```

---

## 📋 Checklist al Agregar Nueva Imagen

- [ ] ¿Es para email? → `static/public/emails/`
- [ ] ¿Es imagen nueva? → `static/public/new/`
- [ ] ¿Formato correcto? (PNG para emails, SVG para web)
- [ ] ¿Tamaño optimizado? (comprimido para web)
- [ ] ¿Nombre descriptivo? (ej: `header-bienvenida.png`)
- [ ] ¿URL absoluta si es para email?

---

## ⚠️ Reglas Importantes

1. **NO modificar** `static/images/` - Ya existe, dejar como está
2. **NO modificar** `static/uploads/` - Archivos subidos por usuarios
3. **Solo usar** `static/public/` para emails y cosas nuevas
4. **Emails siempre** requieren URLs absolutas
5. **PNG recomendado** para emails (mejor compatibilidad)
6. **Optimizar imágenes** antes de subir (comprimir)

---

## 📝 Ejemplos de Templates de Email

### Template de Bienvenida

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Bienvenido</title>
</head>
<body>
    <div class="container">
        <div class="header">
            <!-- Logo desde public/emails/logos/ -->
            <img src="{{ logo_url }}" alt="Logo Easy NodeOne" style="width: 90px;">
            <div class="title">Easy NodeOne</div>
        </div>
        <!-- Resto del contenido -->
    </div>
</body>
</html>
```

**En Python**:

```python
logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
html = render_template_string(template, logo_url=logo_url)
```

---

## 🔗 URLs de Producción

**Base URL**: `https://app.example.com` (o tu dominio de producción)

**Ejemplo de URL completa**:
```
https://app.example.com/static/public/emails/logos/logo-primary.png
```

---

## 📞 Soporte

Si tienes dudas sobre dónde colocar una imagen:
1. Revisa esta guía
2. ¿Es para email? → `static/public/emails/`
3. ¿Es nueva? → `static/public/new/`
4. ¿Ya existe? → NO mover, dejar donde está

---

**Última actualización**: 2025-01-XX  
**Mantenido por**: Equipo de desarrollo Easy NodeOne


