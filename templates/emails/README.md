# 📧 Templates de Email - Easy NodeOne

Este directorio contiene todos los templates HTML para emails del sistema.

## 📁 Estructura

```
templates/emails/
├── sistema/
│   └── bienvenida.html          # Email de bienvenida al registrarse
│
└── eventos/
    ├── registro_evento.html     # Confirmación de registro a evento
    ├── cancelacion_evento.html  # Cancelación de registro a evento
    ├── actualizacion_evento.html # Actualización de información de evento
    ├── confirmacion_cita.html    # Confirmación de cita con asesor
    └── recordatorio_cita.html    # Recordatorio de cita próxima
```

## 🖼️ Imágenes Requeridas

### Logo de Easy NodeOne

**Ubicación**: `static/public/emails/logos/logo-primary.png`

**Requisitos**:
- Formato: PNG (mejor compatibilidad con clientes de email)
- Tamaño recomendado: 90-150px de ancho
- Optimizado para web (comprimido)
- Fondo transparente o blanco

**Cómo subir el logo**:
1. Coloca tu archivo `logo-primary.png` en: `static/public/emails/logos/`
2. El template usará automáticamente la función `get_public_image_url()` para generar la URL

## 💻 Cómo Usar los Templates

### Ejemplo: Email de Bienvenida

```python
from flask import render_template
from app import get_public_image_url, request

def send_welcome_email(user):
    # Generar URLs absolutas (necesarias para emails)
    logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
    base_url = request.url_root.rstrip('/') if request else 'https://app.example.com'
    login_url = f"{base_url}/login"
    
    # Renderizar template
    html = render_template('emails/sistema/bienvenida.html',
                          logo_url=logo_url,
                          user_first_name=user.first_name,
                          user_last_name=user.last_name,
                          login_url=login_url,
                          base_url=base_url,
                          year=datetime.now().year,
                          contact_email='administracion@example.com')
    
    # Enviar email...
    send_email(user.email, 'Bienvenido a Easy NodeOne', html)
```

### Ejemplo: Confirmación de Registro a Evento

```python
def send_event_registration_email(user, event, registration):
    logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
    base_url = request.url_root.rstrip('/') if request else 'https://app.example.com'
    
    html = render_template('emails/eventos/registro_evento.html',
                          logo_url=logo_url,
                          user_first_name=user.first_name,
                          user_last_name=user.last_name,
                          event_title=event.title,
                          event_category=event.category,
                          event_start_date=event.start_date.strftime('%d de %B de %Y'),
                          event_end_date=event.end_date.strftime('%d de %B de %Y'),
                          event_format=event.format,
                          event_location=event.location,
                          event_price=event.base_price,
                          event_currency=event.currency,
                          event_description=event.description,
                          event_registration_url=event.registration_url,
                          event_detail_url=f"{base_url}/events/{event.slug}",
                          event_has_certificate=event.has_certificate,
                          discount_applied=False,
                          base_url=base_url,
                          year=datetime.now().year,
                          contact_email=event.contact_email or 'administracion@example.com')
    
    send_email(user.email, f'Confirmación de Registro - {event.title}', html)
```

### Ejemplo: Confirmación de Cita

```python
def send_appointment_confirmation_email(user, appointment, advisor):
    logo_url = get_public_image_url('emails/logos/logo-primary.png', absolute=True)
    base_url = request.url_root.rstrip('/') if request else 'https://app.example.com'
    
    html = render_template('emails/eventos/confirmacion_cita.html',
                          logo_url=logo_url,
                          user_first_name=user.first_name,
                          user_last_name=user.last_name,
                          appointment_type=appointment.appointment_type.name,
                          appointment_date=appointment.start_datetime.strftime('%d de %B de %Y'),
                          appointment_time=appointment.start_datetime.strftime('%H:%M'),
                          appointment_duration=appointment.appointment_type.duration_minutes,
                          appointment_format='Virtual' if appointment.is_virtual else 'Presencial',
                          advisor_name=f"{advisor.first_name} {advisor.last_name}",
                          advisor_specialization=advisor.specializations,
                          meeting_url=appointment.meeting_url,
                          appointment_notes=appointment.notes,
                          appointments_url=f"{base_url}/appointments",
                          base_url=base_url,
                          year=datetime.now().year,
                          contact_email='administracion@example.com')
    
    send_email(user.email, f'Confirmación de Cita - {appointment.appointment_type.name}', html)
```

## 🎨 Variables Disponibles en Templates

### Variables Comunes (todos los templates)
- `logo_url` - URL absoluta del logo
- `base_url` - URL base del sitio
- `year` - Año actual
- `contact_email` - Email de contacto

### Template: bienvenida.html
- `user_first_name` - Nombre del usuario
- `user_last_name` - Apellido del usuario
- `login_url` - URL para iniciar sesión

### Template: registro_evento.html
- `user_first_name`, `user_last_name`
- `event_title` - Título del evento
- `event_category` - Categoría del evento
- `event_start_date` - Fecha de inicio (formateada)
- `event_end_date` - Fecha de fin (formateada)
- `event_format` - Formato (virtual, presencial, híbrido)
- `event_location` - Ubicación (opcional)
- `event_price` - Precio del evento
- `event_currency` - Moneda (USD, etc.)
- `event_description` - Descripción del evento
- `event_registration_url` - URL de registro externo (opcional)
- `event_detail_url` - URL de detalles del evento
- `event_has_certificate` - Boolean, si incluye certificado
- `discount_applied` - Boolean, si se aplicó descuento
- `discount_amount` - Monto del descuento (si aplica)

### Template: cancelacion_evento.html
- `user_first_name`, `user_last_name`
- `event_title`
- `event_start_date`, `event_end_date`
- `cancellation_reason` - Motivo de cancelación (opcional)
- `events_list_url` - URL a lista de eventos

### Template: actualizacion_evento.html
- `user_first_name`, `user_last_name`
- `event_title`
- `changes` - Lista de cambios (array de strings)
- `event_start_date`, `event_end_date`
- `event_format`, `event_location`
- `event_price`, `event_currency`
- `update_message` - Mensaje adicional (opcional)
- `event_detail_url`

### Template: confirmacion_cita.html
- `user_first_name`, `user_last_name`
- `appointment_type` - Tipo de cita
- `appointment_date` - Fecha (formateada)
- `appointment_time` - Hora (formateada)
- `appointment_duration` - Duración en minutos
- `appointment_format` - Virtual/Presencial
- `advisor_name` - Nombre del asesor
- `advisor_specialization` - Especialización (opcional)
- `meeting_url` - URL de la reunión (opcional)
- `appointment_notes` - Notas adicionales (opcional)
- `appointments_url` - URL a lista de citas

### Template: recordatorio_cita.html
- Todas las variables de `confirmacion_cita.html`
- `hours_until` - Horas hasta la cita

## 🎨 Paleta de Colores

Los templates usan la paleta oficial de Easy NodeOne:
- **Azul Principal**: `#0039ef`
- **Azul Oscuro**: `#0a2a43`
- **Amarillo Dorado**: `#ffc433`
- **Púrpura Oscuro**: `#280f4c`

## 📝 Notas Importantes

1. **URLs Absolutas**: Todos los templates requieren URLs absolutas para imágenes y enlaces (usar `get_public_image_url()` con `absolute=True`)

2. **Formato de Fechas**: Usar formato legible en español:
   ```python
   event.start_date.strftime('%d de %B de %Y')  # "15 de Enero de 2025"
   ```

3. **Compatibilidad**: Los templates están diseñados para ser compatibles con la mayoría de clientes de email (Gmail, Outlook, Apple Mail, etc.)

4. **Responsive**: Los templates son responsive y se adaptan a dispositivos móviles

5. **Testing**: Siempre probar los emails en diferentes clientes antes de enviar en producción

## 🔗 Referencias

- Ver `GUIA_IMAGENES_PUBLICAS.md` para más información sobre imágenes
- Ver `backend/app.py` para la función `get_public_image_url()`


