# 📢 Imágenes de Anuncios

Esta carpeta contiene las imágenes para los anuncios/flayers que se muestran en el dashboard.

## 📁 Ubicación
```
static/public/announcements/
```

## 📝 Cómo usar

### Opción 1: Subir imagen al servidor (Recomendado)

1. **Sube tu imagen** a esta carpeta:
   ```
   static/public/announcements/promo-diciembre-2024.jpg
   ```

2. **En el formulario de anuncios**, usa la URL relativa:
   ```
   /static/public/announcements/promo-diciembre-2024.jpg
   ```
   
   O la URL completa:
   ```
   https://app.example.com/static/public/announcements/promo-diciembre-2024.jpg
   ```

### Opción 2: Usar Google Drive (URL directa de imagen)

**⚠️ IMPORTANTE**: No uses URLs de carpetas. Necesitas la URL directa de la imagen.

**Cómo obtener la URL correcta de Google Drive:**

1. Abre la imagen en Google Drive
2. Haz clic derecho en la imagen → "Obtener enlace"
3. Cambia el modo de acceso a "Cualquiera con el enlace"
4. Copia el ID del archivo de la URL (ej: `1lRMsKt0X_ys0Y-0XJ8q3hJ-6URVTxWDE`)
5. Usa este formato:
   ```
   https://drive.google.com/uc?export=view&id=ID_DEL_ARCHIVO
   ```
   
   Ejemplo:
   ```
   https://drive.google.com/uc?export=view&id=1lRMsKt0X_ys0Y-0XJ8q3hJ-6URVTxWDE
   ```

### Opción 3: Usar otro servicio de hosting

Puedes usar cualquier servicio que proporcione URLs directas de imágenes:
- Imgur
- Cloudinary
- AWS S3
- Otro servidor de imágenes

## ✅ Formatos recomendados

- **PNG**: Para imágenes con transparencia
- **JPG**: Para fotografías (mejor compresión)
- **WebP**: Formato moderno (mejor compresión)

## 📏 Tamaños recomendados

- **Ancho**: 400-800px
- **Alto**: 300-600px
- **Peso**: Máximo 500KB (optimizar antes de subir)

## 🔗 Ejemplo de URL en el formulario

Si subiste `promo-diciembre.jpg` a esta carpeta, usa:
```
/static/public/announcements/promo-diciembre.jpg
```

O la URL completa:
```
https://app.example.com/static/public/announcements/promo-diciembre.jpg
```

