# 📊 Sistema de Analytics y Reportes

## ✅ Funcionalidades Implementadas

### 1. **Analytics Avanzados** ✅
- Dashboard completo de métricas en tiempo real
- Análisis de usuarios, membresías, pagos y eventos
- Filtros por rango de fechas
- Métricas actualizadas automáticamente cada 30 segundos

### 2. **Reportes Personalizables** ✅
- Generación de reportes de:
  - Usuarios
  - Membresías
  - Pagos
  - Eventos
- Selección de columnas personalizadas
- Filtros por rango de fechas

### 3. **Exportación de Datos** ✅
- **CSV**: Compatible con Excel y Google Sheets
- **Excel (.xlsx)**: Formato profesional con formato
- **PDF**: Reportes listos para impresión
- **JSON**: Para integración con otras aplicaciones

### 4. **Dashboard de Métricas en Tiempo Real** ✅
- Métricas de las últimas 24 horas
- Actualización automática cada 30 segundos
- Gráficos de tendencias (Chart.js)
- Visualización de datos por categorías

## 📁 Archivos Creados

### Backend
- `backend/analytics.py` - Servicio de analytics y métricas
- `backend/report_generator.py` - Generador de reportes en múltiples formatos

### Templates
- `templates/admin/analytics.html` - Dashboard de analytics
- `templates/admin/reports.html` - Página de generación de reportes

### Rutas Agregadas
- `/admin/analytics` - Dashboard principal de analytics
- `/api/admin/analytics/realtime` - API para métricas en tiempo real
- `/api/admin/analytics/metrics` - API para métricas con filtros
- `/admin/reports` - Página de reportes personalizables
- `/api/admin/reports/generate` - API para generar reportes

## 🚀 Instalación de Dependencias

Para usar todas las funcionalidades, instala las dependencias opcionales:

```bash
# Para exportación a Excel
pip install pandas openpyxl

# Para exportación a PDF
pip install reportlab
```

O instala todas de una vez:
```bash
pip install -r requirements.txt
```

## 📊 Métricas Disponibles

### Usuarios
- Total de usuarios
- Usuarios activos
- Nuevos usuarios (en período)
- Usuarios por país

### Membresías
- Total de membresías
- Membresías activas/expiradas/pausadas
- Nuevas membresías (en período)
- Distribución por tipo

### Pagos
- Ingresos totales
- Total de pagos
- Pagos exitosos
- Distribución por método de pago
- Tendencia mensual (últimos 12 meses)

### Eventos
- Total de eventos
- Total de registros
- Distribución por estado
- Eventos más populares

## 🎯 Uso

### Acceder al Dashboard de Analytics
1. Inicia sesión como administrador
2. Ve a "Panel de Administración"
3. Haz clic en "Ver Analytics"
4. Usa los filtros de fecha para analizar períodos específicos

### Generar un Reporte
1. Ve a "Exportar Reportes" desde el panel de administración
2. Selecciona el tipo de reporte
3. Configura el rango de fechas (opcional)
4. Selecciona el formato de exportación
5. Elige las columnas a incluir
6. Haz clic en "Generar y Descargar Reporte"

## 🔄 Actualización en Tiempo Real

El dashboard de analytics se actualiza automáticamente cada 30 segundos mostrando:
- Nuevos usuarios en las últimas 24 horas
- Nuevas membresías en las últimas 24 horas
- Nuevos pagos en las últimas 24 horas
- Ingresos de las últimas 24 horas

## 📝 Notas

- Los reportes grandes pueden tardar unos segundos en generarse
- El formato PDF requiere más tiempo de procesamiento
- Las métricas en tiempo real se calculan sobre las últimas 24 horas
- Los filtros de fecha son opcionales; si no se especifican, se incluyen todos los registros

## 🛠️ Personalización

Puedes extender el sistema agregando:
- Nuevos tipos de reportes en `api_generate_report()`
- Nuevas métricas en `AnalyticsService`
- Nuevos formatos de exportación en `ReportGenerator`
- Nuevos gráficos en el dashboard usando Chart.js

