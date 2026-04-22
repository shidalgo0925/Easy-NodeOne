# Sistema de Notificaciones y Correos Electrónicos

## 📧 Descripción General

Sistema completo de notificaciones y correos electrónicos para Easy NodeOne que incluye:

- **Motor de notificaciones** con múltiples tipos de eventos
- **Plantillas HTML profesionales** para correos electrónicos
- **Servicio de correo** con reintentos automáticos y manejo de errores
- **Sistema de tareas programadas** para recordatorios y verificaciones automáticas

## 🏗️ Arquitectura

### Módulos Principales

1. **`email_templates.py`** - Plantillas HTML para diferentes tipos de correos
2. **`email_service.py`** - Servicio centralizado de envío con reintentos
3. **`NotificationEngine`** (en `app.py`) - Motor de notificaciones
4. **`notification_scheduler.py`** - Tareas programadas para verificaciones automáticas

## 📋 Tipos de Notificaciones Implementadas

### Membresías
- ✅ **Pago confirmado** - Cuando se procesa un pago de membresía
- ✅ **Membresía por expirar** - Alertas a 30, 15, 7 y 1 día antes
- ✅ **Membresía expirada** - Notificación cuando expira
- ✅ **Membresía renovada** - Confirmación de renovación

### Eventos
- ✅ **Registro a evento** - Notificación a responsables y usuario
- ✅ **Cancelación de registro** - Notificación a responsables y usuario
- ✅ **Confirmación de registro** - Cuando se confirma un registro
- ✅ **Actualización de evento** - Cuando se modifican detalles del evento

### Citas (Appointments)
- ✅ **Confirmación de cita** - Cuando se confirma una cita
- ✅ **Recordatorio de cita** - Recordatorios a 24 y 48 horas antes

### Sistema
- ✅ **Bienvenida** - Email de bienvenida a nuevos usuarios
- ✅ **Restablecimiento de contraseña** - (Plantilla disponible)

## 🚀 Uso

### Envío Manual de Notificaciones

```python
from backend.app import NotificationEngine, User, Subscription

# Notificar pago de membresía
NotificationEngine.notify_membership_payment(user, payment, subscription)

# Notificar membresía por expirar
NotificationEngine.notify_membership_expiring(user, subscription, days_left=7)

# Notificar bienvenida
NotificationEngine.notify_welcome(user)

# Notificar registro a evento
NotificationEngine.notify_event_registration_to_user(event, user, registration)
```

### Tareas Programadas

Ejecutar el script de scheduler para verificar membresías expirando y enviar recordatorios:

```bash
cd backend
python notification_scheduler.py
```

Para ejecutar automáticamente, configurar un cron job:

```bash
# Ejecutar diariamente a las 9:00 AM
0 9 * * * cd /ruta/al/proyecto/backend && python notification_scheduler.py
```

## 📧 Configuración de Correo

Las variables de entorno necesarias están en `config.py`:

```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')
```

### Configurar Gmail

1. Habilitar autenticación de 2 factores
2. Generar contraseña de aplicación
3. Usar la contraseña de aplicación como `MAIL_PASSWORD`

## 🎨 Plantillas de Correo

Las plantillas están en `backend/email_templates.py` e incluyen:

- Diseño responsive y profesional
- Logo y branding de Easy NodeOne
- Estilos CSS inline para compatibilidad
- Botones de acción con enlaces
- Información estructurada en cajas destacadas

### Personalizar Plantillas

Las funciones de plantilla retornan HTML completo. Para modificar:

```python
def get_custom_email(user, data):
    content = f"""
        <h2>Título Personalizado</h2>
        <p>Contenido...</p>
    """
    return get_email_template_base().format(
        subject="Asunto del Correo",
        content=content,
        year=datetime.now().year
    )
```

## 🔧 API de Notificaciones

### Obtener Notificaciones

```
GET /api/notifications?type=all&status=unread&limit=50
```

Parámetros:
- `type`: Tipo de notificación (all, membership_payment, event_registration, etc.)
- `status`: Estado (all, read, unread)
- `limit`: Número máximo de resultados (default: 50)

### Marcar como Leída

```
POST /api/notifications/{id}/read
```

### Marcar Todas como Leídas

```
POST /api/notifications/read-all
```

### Eliminar Notificación

```
DELETE /api/notifications/{id}
```

## 📊 Base de Datos

### Modelo Notification

```python
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 🔄 Integración con Rutas Existentes

El sistema se integra automáticamente con:

- ✅ Registro de usuarios → Envía bienvenida
- ✅ Procesamiento de pagos → Envía confirmación
- ✅ Registro a eventos → Notifica a responsables y usuario
- ✅ Cancelación de eventos → Notifica a usuarios registrados
- ✅ Confirmación de citas → Envía confirmación

## 🛠️ Mantenimiento

### Verificar Estado del Sistema

```python
from backend.app import Notification, db

# Notificaciones no enviadas
pending = Notification.query.filter_by(email_sent=False).count()

# Notificaciones no leídas
unread = Notification.query.filter_by(is_read=False).count()
```

### Limpiar Notificaciones Antiguas

```python
# Eliminar notificaciones leídas de más de 90 días
from datetime import datetime, timedelta

old_date = datetime.utcnow() - timedelta(days=90)
Notification.query.filter(
    Notification.is_read == True,
    Notification.created_at < old_date
).delete()
db.session.commit()
```

## 📝 Logs y Debugging

El sistema registra información en la consola:

- ✅ Envíos exitosos
- ❌ Errores de envío
- ⚠️ Advertencias (ej: sin destinatarios)

Para habilitar logging detallado:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔒 Seguridad

- Las notificaciones solo son accesibles por el usuario propietario
- Los correos se envían solo a direcciones verificadas
- Las plantillas sanitizan automáticamente el contenido HTML
- Los reintentos previenen pérdida de notificaciones importantes

## 📈 Mejoras Futuras

- [ ] Sistema de preferencias de notificaciones por usuario
- [ ] Notificaciones push en tiempo real
- [ ] Dashboard de estadísticas de notificaciones
- [ ] Plantillas personalizables por administrador
- [ ] Integración con servicios de email externos (SendGrid, Mailgun)

## 📞 Soporte

Para problemas o preguntas sobre el sistema de notificaciones:
- Revisar logs en la consola
- Verificar configuración de correo en variables de entorno
- Consultar documentación de Flask-Mail

---

**Easy NodeOne** - Sistema de Notificaciones v1.0

