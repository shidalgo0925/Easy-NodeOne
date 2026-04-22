# 📹 Videos para Guías Visuales

Esta carpeta contiene los videos que se muestran en las guías visuales interactivas del sistema de ayuda.

## 📁 Ubicación
```
static/videos/
```

## 🎥 Cómo Subir un Video

### Opción 1: Usando SCP (desde tu computadora local)

```bash
# Desde tu computadora local, ejecuta:
scp ruta/a/tu/video.mp4 usuario@servidor:/var/www/nodeone/static/videos/registro-usuarios.mp4
```

### Opción 2: Usando SFTP

1. Conecta con un cliente SFTP (FileZilla, WinSCP, etc.)
2. Navega a: `/var/www/nodeone/static/videos/`
3. Sube tu archivo de video

### Opción 3: Desde el servidor directamente

Si ya tienes el video en el servidor:

```bash
# Mover el video a esta carpeta
mv /ruta/origen/video.mp4 /var/www/nodeone/static/videos/registro-usuarios.mp4
```

## 📝 Video de Registro de Usuarios

**Nombre del archivo**: `registro-usuarios.mp4`

**Ruta en el código**: `/static/videos/registro-usuarios.mp4`

Este video se muestra en la guía visual de registro de nuevos usuarios.

## ✅ Formatos Recomendados

- **MP4** (H.264): Formato más compatible
- **WebM**: Formato moderno, mejor compresión
- **Resolución**: 1920x1080 (Full HD) o 1280x720 (HD)
- **Peso**: Intenta mantenerlo bajo 50MB para mejor rendimiento

## 🔧 Optimización de Videos

Si el video es muy pesado, puedes optimizarlo:

```bash
# Usando ffmpeg (si está instalado)
ffmpeg -i video-original.mp4 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k registro-usuarios.mp4
```

## 📋 Archivos Actuales

- `registro-usuarios.mp4` - Video del proceso de registro de nuevos usuarios

## 🔗 Cómo se Usa en el Código

El video se referencia en `templates/help.html` en el objeto `visualGuides`:

```javascript
video: '/static/videos/registro-usuarios.mp4'
```

El código detecta automáticamente que es un archivo local y lo muestra usando el reproductor HTML5 `<video>`.


