# Resumen Funcional - Sistema nodeone

> **Propósito**: Documento de referencia rápida para entender qué hace el sistema y cómo funciona.

---

## 🎯 Propósito del Sistema

Sistema completo de gestión de membresías para Easy NodeOne que incluye:
- Gestión de usuarios y membresías
- Sistema de pagos con Stripe
- Gestión de eventos y citas
- Sistema de notificaciones y emails
- Panel de administración completo

---

## 🏗️ Arquitectura Técnica

### Stack Tecnológico
- **Backend**: Flask (Python 3)
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **ORM**: SQLAlchemy
- **Autenticación**: Flask-Login
- **Pagos**: Stripe API
- **Emails**: Flask-Mail + EmailService personalizado
- **Frontend**: Bootstrap 5 + HTML/CSS + Jinja2 templates

### Estructura Principal
```
backend/app.py (4385 líneas) - Aplicación principal Flask
├── Modelos de BD (25+ modelos)
├── Rutas públicas y autenticadas
├── Rutas de administración
├── Motor de notificaciones (NotificationEngine)
├── Sistema de emails
└── APIs REST

backend/event_routes.py - Rutas de eventos
backend/appointment_routes.py - Rutas de citas
backend/email_service.py - Servicio de envío de emails
backend/email_templates.py - Templates HTML de emails
```

---

## 📊 Modelos de Base de Datos Principales

### Usuarios y Autenticación
- **User**: Usuarios del sistema
  - Campos: email, password_hash, first_name, last_name, phone
  - Roles: is_admin, is_advisor
  - Verificación: email_verified, email_verification_token

### Membresías y Pagos
- **Membership**: Membresías (sistema legacy)
- **Subscription**: Suscripciones activas (sistema nuevo)
  - Tipos: basic (gratis), pro ($60/año), premium ($120/año), deluxe ($200/año)
- **Payment**: Registro de pagos con Stripe
- **Benefit**: Beneficios por tipo de membresía

### Eventos
- **Event**: Eventos con flujo de 5 pasos (Evento, Descripción, Publicidad, Certificado, Kahoot)
- **EventRegistration**: Registros a eventos
- **EventParticipant**: Participantes con categorías
- **EventSpeaker**: Ponentes/Exponentes
- **EventCertificate**: Certificados generados
- **Discount**: Descuentos reutilizables
- **EventDiscount**: Relación eventos-descuentos

### Citas (Appointments)
- **AppointmentType**: Tipos de servicios configurables
- **Advisor**: Perfiles de asesores internos
- **AdvisorAvailability**: Disponibilidad semanal de asesores
- **AppointmentSlot**: Slots de tiempo disponibles
- **Appointment**: Reservas realizadas por miembros
- **AppointmentParticipant**: Participantes en citas grupales
- **AppointmentPricing**: Reglas de precio por membresía

### Sistema de Emails y Notificaciones
- **EmailLog**: Registro completo de todos los emails enviados
- **EmailConfig**: Configuración SMTP (editable desde panel)
- **EmailTemplate**: Templates editables de correos
- **Notification**: Notificaciones del sistema
- **NotificationSettings**: Configuración de notificaciones (activar/desactivar)

### Carrito de Compras
- **Cart**: Carrito del usuario
- **CartItem**: Items en el carrito

### Otros
- **ActivityLog**: Log de actividades administrativas

---

## 🔄 Flujos Principales

### 1. Registro de Usuario
```
Usuario completa formulario
  ↓
Validación estricta de email
  ↓
Creación de usuario (email_verified=False)
  ↓
Generación de token de verificación
  ↓
Envío de email de verificación
  ↓
Usuario verifica email → email_verified=True
  ↓
Envío de email de bienvenida
```

### 2. Compra de Membresía
```
Usuario selecciona membresía
  ↓
Agregar al carrito
  ↓
Checkout (requiere email verificado)
  ↓
Crear Payment Intent (Stripe o modo demo)
  ↓
Procesar pago
  ↓
Crear Subscription
  ↓
Enviar notificación de confirmación
```

### 3. Registro a Evento
```
Usuario se registra a evento
  ↓
Calcular precio según membresía (descuentos)
  ↓
Crear EventRegistration
  ↓
Notificar a responsables (moderador, admin, expositor)
  ↓
Notificar al usuario
  ↓
Enviar emails de confirmación
```

### 4. Reserva de Cita
```
Usuario selecciona tipo de cita
  ↓
Selecciona asesor
  ↓
Ve slots disponibles
  ↓
Reserva slot
  ↓
Calcular precio según membresía
  ↓
Si requiere pago → procesar
  ↓
Cita en estado "pending"
  ↓
Asesor confirma → estado "confirmed"
  ↓
Enviar notificaciones
```

### 5. Sistema de Emails
```
Evento del sistema (registro, pago, etc.)
  ↓
NotificationEngine verifica si está habilitada
  ↓
EmailService envía con reintentos (3 intentos)
  ↓
Registra en EmailLog
  ↓
Crea Notification en BD
```

---

## 🔧 Componentes Clave

### NotificationEngine
Motor centralizado de notificaciones con 13 tipos:
- **Sistema**: welcome
- **Membresías**: membership_payment, membership_expiring, membership_expired, membership_renewed
- **Eventos**: event_registration, event_registration_user, event_cancellation, event_cancellation_user, event_confirmation, event_update
- **Citas**: appointment_confirmation, appointment_reminder

Cada notificación:
1. Verifica si está habilitada (NotificationSettings)
2. Crea Notification en BD
3. Genera HTML con templates
4. Envía email usando EmailService
5. Registra en EmailLog

### EmailService
Servicio de envío con:
- Reintentos automáticos (3 intentos con backoff)
- Registro automático en EmailLog
- Manejo de errores robusto

### Sistema de Precios
- **Eventos**: Descuentos por membresía (Básico 0%, Pro 10%, Premium 20%, Deluxe 30%)
- **Citas**: Precios configurables, pueden estar incluidos en membresía o con descuento

---

## 🛣️ Rutas Principales

### Públicas
- `/` - Página principal
- `/register` - Registro
- `/login` - Login
- `/verify-email/<token>` - Verificar email

### Autenticadas
- `/dashboard` - Panel del usuario
- `/membership` - Gestión de membresía
- `/benefits` - Beneficios
- `/services` - Servicios
- `/office365` - Office 365
- `/profile` - Perfil
- `/settings` - Configuración
- `/notifications` - Notificaciones
- `/cart` - Carrito de compras
- `/checkout` - Checkout

### Administración
- `/admin` - Panel admin
- `/admin/users` - Gestión de usuarios
- `/admin/memberships` - Gestión de membresías
- `/admin/messaging` - Gestión de emails
- `/admin/email` - Configuración SMTP y templates
- `/admin/notifications` - Configuración de notificaciones
- `/admin/events/*` - Gestión de eventos
- `/admin/appointments/*` - Gestión de citas

### APIs
- `/api/user/membership` - Info de membresía
- `/api/notifications` - Notificaciones del usuario
- `/api/admin/messaging/stats` - Estadísticas de emails
- `/api/admin/email/*` - APIs de configuración de email
- `/api/admin/notifications/*` - APIs de notificaciones

---

## 📧 Sistema de Emails

### Configuración
- Configurable desde `/admin/email`
- Soporta Gmail y Office 365
- Puede usar variables de entorno o BD
- Templates editables desde panel

### Templates Disponibles
- Bienvenida
- Verificación de email
- Confirmación de pago
- Membresía por expirar/expirada/renovada
- Registro/cancelación de evento
- Confirmación/recordatorio de cita
- Restablecimiento de contraseña

### Logging
- Todos los emails se registran en EmailLog
- Incluye: destinatario, asunto, contenido, tipo, estado, errores, reintentos

---

## 🔒 Seguridad

- Autenticación con Flask-Login
- Contraseñas hasheadas (Werkzeug)
- Verificación de email requerida para acciones importantes
- Decoradores: `@login_required`, `@admin_required`, `@email_verified_required`
- Validación estricta de emails (bloquea dominios temporales)
- Sistema de licencias (opcional)

---

## 📦 Dependencias Principales

```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-Mail==0.9.1
Werkzeug==2.3.7
stripe==7.8.0
python-dotenv==1.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.7
```

---

## 🚀 Despliegue

- **Servicio systemd**: `nodeone.service`
- **Puerto**: 9000 (desarrollo) / 8080 (producción)
- **Proxy**: Nginx (app.example.com)
- **Base de datos**: SQLite en `backend/instance/membership_legacy.db`

---

## 📝 Notas Importantes

1. **Modo Demo**: El sistema tiene modo demo para pagos (no requiere Stripe real)
2. **Email Service**: Puede funcionar sin templates (fallback básico)
3. **Blueprints**: Eventos y citas están en archivos separados
4. **Migraciones**: Varios scripts de migración en `backend/`
5. **Backups**: Se guardan en `backups/`

---

## 🔍 Archivos Clave para Entender

1. `backend/app.py` - Aplicación principal (4385 líneas)
2. `backend/event_routes.py` - Rutas de eventos
3. `backend/appointment_routes.py` - Rutas de citas
4. `backend/email_service.py` - Servicio de emails
5. `backend/email_templates.py` - Templates de emails
6. `README.md` - Documentación general
7. `ANALISIS_ESTRUCTURA.md` - Análisis detallado de estructura
8. `ANALISIS_MOTOR_MENSAJERIA.md` - Sistema de mensajería
9. `PLAN_GESTION_EMAILS.md` - Plan de gestión de emails

---

**Última actualización**: 2025-01-XX
**Versión del sistema**: 1.0.0





