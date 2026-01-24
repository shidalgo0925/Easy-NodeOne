# Guía para Agregar Contenido Multimedia a las Guías Visuales

Este documento explica cómo agregar videos y audios a las guías visuales interactivas del sistema de ayuda.

## 📍 Ubicación

Las guías visuales están en: `templates/help.html`

## 🎥 Agregar Videos

### Opción 1: YouTube

1. Sube tu video a YouTube
2. Obtén la URL del video (ej: `https://www.youtube.com/watch?v=VIDEO_ID`)
3. Convierte a formato embed: `https://www.youtube.com/embed/VIDEO_ID`
4. Actualiza la URL en el objeto `visualGuides` en el JavaScript

### Opción 2: Vimeo

1. Sube tu video a Vimeo
2. Obtén la URL de embed
3. Actualiza en el código JavaScript

### Opción 3: Servidor Propio

1. Sube el video a `static/videos/`
2. Usa la ruta: `/static/videos/nombre-video.mp4`
3. Actualiza en el código JavaScript

### Ejemplo de Actualización

```javascript
// En templates/help.html, buscar:
visualGuides = {
    'register': {
        steps: [
            {
                video: 'https://ejemplo.com/videos/registro-paso1.mp4',  // ← Cambiar esta URL
                audio: 'https://ejemplo.com/audio/registro-paso1.mp3'   // ← Cambiar esta URL
            }
        ]
    }
}

// Cambiar a:
visualGuides = {
    'register': {
        steps: [
            {
                video: 'https://www.youtube.com/embed/ABC123XYZ',  // ← URL real
                audio: '/static/audio/registro-paso1.mp3'          // ← URL real
            }
        ]
    }
}
```

## 🎵 Agregar Audios

### Opción 1: Servidor Propio (Recomendado)

1. Sube el archivo de audio a `static/audio/`
2. Formatos soportados: MP3, OGG, WAV
3. Usa la ruta: `/static/audio/nombre-audio.mp3`

### Opción 2: Servicio Externo

1. Sube a un servicio de hosting de audio
2. Obtén la URL directa del archivo
3. Actualiza en el código JavaScript

### Estructura de Carpetas Recomendada

```
static/
├── videos/
│   ├── registro-paso1.mp4
│   ├── registro-paso2.mp4
│   ├── membresia-paso1.mp4
│   └── ...
└── audio/
    ├── registro-paso1.mp3
    ├── registro-paso2.mp3
    ├── membresia-paso1.mp3
    └── ...
```

## 📝 Procedimientos Disponibles

Actualmente hay 6 guías visuales configuradas:

1. **register** - Registro de Usuario (3 pasos)
2. **membership** - Compra de Membresía (4 pasos)
3. **payment** - Proceso de Pago (3 pasos)
4. **events** - Registro a Eventos (3 pasos)
5. **appointments** - Reserva de Citas (4 pasos)
6. **admin-payments** - Configuración de Métodos de Pago (4 pasos)

## 🎬 Crear Videos

### Recomendaciones Técnicas

- **Formato**: MP4 (H.264)
- **Resolución**: 1920x1080 (Full HD) o 1280x720 (HD)
- **Duración**: 1-3 minutos por paso
- **Audio**: Narración clara, música de fondo opcional
- **Subtítulos**: Opcional pero recomendado

### Contenido Sugerido

Cada video debe mostrar:
1. Pantalla completa del proceso
2. Cursor y clics visibles
3. Narración explicando cada acción
4. Texto superpuesto con tips importantes
5. Transiciones suaves entre pasos

### Herramientas Recomendadas

- **Grabación**: OBS Studio, Camtasia, ScreenFlow
- **Edición**: DaVinci Resolve, Adobe Premiere, Final Cut
- **Narración**: Audacity, Adobe Audition

## 🎙️ Crear Audios

### Recomendaciones Técnicas

- **Formato**: MP3 (128-192 kbps)
- **Duración**: 30-90 segundos por paso
- **Calidad**: Audio claro, sin ruido de fondo
- **Idioma**: Español (o el idioma principal)

### Contenido Sugerido

Cada audio debe incluir:
1. Introducción del paso
2. Explicación de la acción
3. Tips importantes
4. Confirmación de completado

### Herramientas Recomendadas

- **Grabación**: Audacity, GarageBand, Adobe Audition
- **Mejora**: Reducción de ruido, normalización de volumen

## 🔧 Personalización Avanzada

### Agregar Nuevas Guías

1. Agrega una nueva tarjeta en la sección "Guía Visual Interactiva"
2. Agrega el objeto correspondiente en `visualGuides`
3. Define los pasos con sus videos y audios

### Ejemplo de Nueva Guía

```javascript
// En el HTML, agregar tarjeta:
<div class="col-md-6 col-lg-4">
    <div class="card border h-100 visual-guide-card" data-procedure="nueva-guia">
        ...
    </div>
</div>

// En el JavaScript, agregar objeto:
visualGuides['nueva-guia'] = {
    title: 'Nueva Guía - Título',
    steps: [
        {
            number: 1,
            icon: 'fa-icon',
            title: 'Título del Paso',
            description: 'Descripción del paso',
            visual: '<div>...</div>',
            video: 'URL_DEL_VIDEO',
            audio: 'URL_DEL_AUDIO'
        }
    ]
};
```

## 📊 Estadísticas y Seguimiento

### Agregar Analytics

Puedes agregar seguimiento de reproducción:

```javascript
function playVideo(url) {
    // Tracking
    if (typeof gtag !== 'undefined') {
        gtag('event', 'video_play', {
            'video_url': url
        });
    }
    // Reproducir video
    window.open(url, '_blank');
}
```

## ✅ Checklist de Implementación

- [ ] Videos grabados y editados
- [ ] Audios grabados y editados
- [ ] Archivos subidos al servidor
- [ ] URLs actualizadas en el código
- [ ] Pruebas de reproducción realizadas
- [ ] Subtítulos agregados (opcional)
- [ ] Analytics configurado (opcional)

## 🚀 Próximos Pasos

1. **Fase 1**: Crear videos básicos (pantalla + narración)
2. **Fase 2**: Agregar efectos y transiciones
3. **Fase 3**: Agregar subtítulos y traducciones
4. **Fase 4**: Optimizar para móviles
5. **Fase 5**: Agregar más guías según necesidad

## 📞 Soporte

Para ayuda con la implementación de contenido multimedia, contacta al equipo de desarrollo.

---

**Última actualización**: Enero 2025

