# 📋 Descripción Detallada del Sistema de Membresía RelaticPanama

## 🎯 Visión General

Sistema completo de gestión de membresías para **RelaticPanama** (Red Latinoamericana de Investigaciones Cualitativas) desarrollado en Flask (Python). El sistema gestiona usuarios, membresías, pagos, eventos, citas, notificaciones y múltiples funcionalidades administrativas.

---

## 🗄️ Modelos de Base de Datos (34 Modelos)

### 👤 **Gestión de Usuarios**
1. **User** - Usuarios del sistema
   - Información personal (nombre, email, teléfono, país, cédula/pasaporte)
   - Autenticación y verificación de email
   - Roles: usuario normal, administrador, asesor
   - Etiquetas y grupos de usuarios
   - Relación con membresías, pagos, eventos y citas

### 💳 **Sistema de Membresías y Pagos**
2. **Membership** - Membresías (sistema legacy)
   - Tipos: basic, pro, premium, deluxe
   - Fechas de inicio y fin
   - Estado de pago

3. **Subscription** - Suscripciones activas (sistema actual)
   - Tipos de membresía
   - Estado (active, expired, cancelled)
   - Fechas de vigencia
   - Vinculado a pagos

4. **Payment** - Registro de pagos
   - Múltiples métodos de pago (Stripe, PayPal, Banco General, Yappy, Interbank)
   - Estados: pending, succeeded, failed, cancelled
   - Referencias de pago y URLs
   - Metadata y comprobantes
   - Fecha de pago completado

5. **PaymentConfig** - Configuración de métodos de pago
   - Credenciales de Stripe, PayPal, Banco General, Yappy
   - Configuración desde BD o variables de entorno
   - Modo activo/inactivo

### 🎫 **Sistema de Descuentos**
6. **Discount** - Descuentos reutilizables
   - Descuentos por tipo de membresía (Básico, Pro, R, DX)
   - Descuentos por categoría (evento, cita, servicio)
   - Aplicación automática o manual
   - **Descuento Maestro** (is_master): descuento global automático
   - Límites de uso y fechas de vigencia

7. **EventDiscount** - Relación eventos-descuentos
   - Prioridad de aplicación
   - Vinculación muchos a muchos

8. **DiscountCode** - Códigos promocionales manuales
   - Códigos únicos (generación manual o automática)
   - Tipos: porcentaje o fijo
   - Alcance: todo el sistema, solo eventos, solo membresías, solo citas
   - Límites: total y por usuario
   - Fechas de vigencia
   - Historial de uso

9. **DiscountApplication** - Historial de aplicación de códigos
   - Usuario que aplicó el código
   - Montos (original, descuento, final)
   - Pago asociado
   - Fecha de aplicación

### 🎉 **Sistema de Eventos**
10. **Event** - Eventos principales
    - Información completa (título, descripción, fechas, ubicación)
    - Flujo de 5 pasos: Evento, Descripción, Publicidad, Certificado, Kahoot
    - Roles: creador, moderador, administrador, expositor
    - Capacidad y registro
    - Estado de publicación (draft, published, archived)
    - Precios base y descuentos por membresía
    - Generación de salidas (carteles, revistas, libros)

11. **EventImage** - Imágenes de galería
    - Múltiples imágenes por evento
    - Imagen principal y galería

12. **EventParticipant** - Participantes de eventos
    - Categorías: participant, attendee, speaker
    - Check-in y check-out
    - Fecha de registro

13. **EventSpeaker** - Expositores/Conferencistas
    - Información del expositor
    - Biografía y foto
    - Vinculado a eventos

14. **EventCertificate** - Certificados de eventos
    - Generación de certificados
    - Plantillas personalizables

15. **EventWorkshop** - Talleres dentro de eventos
    - Información del taller
    - Horarios y capacidad

16. **EventTopic** - Temas/Tópicos de eventos
    - Categorización de eventos
    - Tags y etiquetas

17. **EventRegistration** - Registros a eventos
    - Estado de registro (pending, confirmed, cancelled)
    - Información adicional del participante
    - Fecha de registro

### 📅 **Sistema de Citas/Appointments**
18. **Advisor** - Asesores disponibles
    - Información del asesor
    - Especialidades
    - Disponibilidad

19. **AppointmentType** - Tipos de citas
    - Consultoría, asesoría, revisión, etc.
    - Duración y precios
    - Descripción

20. **AppointmentAdvisor** - Relación citas-asesores
    - Asignación de asesores a tipos de citas

21. **AdvisorAvailability** - Disponibilidad de asesores
    - Horarios disponibles
    - Días de la semana
    - Zona horaria

22. **AppointmentPricing** - Precios de citas
    - Precios por tipo de membresía
    - Descuentos aplicables

23. **AppointmentSlot** - Horarios disponibles
    - Slots de tiempo
    - Disponibilidad
    - Reservas

24. **Appointment** - Citas programadas
    - Usuario y asesor
    - Tipo y fecha/hora
    - Estado (pending, confirmed, completed, cancelled)
    - Notas y recordatorios

25. **AppointmentParticipant** - Participantes de citas
    - Múltiples participantes
    - Roles

### 🛒 **Sistema de Carrito de Compras**
26. **Cart** - Carrito de compras
    - Un carrito por usuario
    - Códigos de descuento aplicados
    - Descuento maestro aplicado
    - Cálculo de totales con descuentos

27. **CartItem** - Items del carrito
    - Tipos: membership, event, service
    - Precio unitario y cantidad
    - Metadata del producto

### 📧 **Sistema de Notificaciones y Email**
28. **Notification** - Notificaciones del sistema
    - Tipos: membership, event, appointment, payment, system
    - Estado de envío de email
    - Prioridad
    - Fechas de creación y envío

29. **EmailLog** - Historial de emails enviados
    - Destinatario y asunto
    - Tipo de email
    - Estado (sent, failed, pending)
    - Reintentos
    - Errores
    - Contenido y fecha de envío

30. **EmailConfig** - Configuración de servidor de email
    - SMTP (Office 365, Gmail, etc.)
    - Credenciales
    - Configuración desde BD

31. **EmailTemplate** - Plantillas de email personalizables
    - Templates para diferentes tipos de emails
    - Versiones personalizadas y por defecto
    - HTML y texto plano

32. **NotificationSettings** - Configuraciones de notificaciones
    - Preferencias por tipo de notificación
    - Activar/desactivar notificaciones
    - Configuración por usuario

### 🎬 **Sistema Multimedia**
33. **MediaConfig** - Configuración de multimedia
    - Videos y audios para guías visuales
    - Procedimientos paso a paso
    - URLs de recursos multimedia
    - Estado activo/inactivo

### 📊 **Logs y Auditoría**
34. **ActivityLog** - Registro de actividades
    - Acciones del sistema
    - Usuario y timestamp
    - Tipo de acción
    - Detalles

---

## 🚀 Funcionalidades Principales

### 👥 **Para Usuarios**

#### **Autenticación y Perfil**
- ✅ Registro con validación de email
- ✅ Inicio de sesión seguro
- ✅ Verificación de email obligatoria
- ✅ Recuperación de contraseña
- ✅ Perfil personalizable
- ✅ Gestión de información (país, cédula/pasaporte)

#### **Dashboard Personalizado**
- ✅ Vista de membresía activa
- ✅ Días activos y días restantes
- ✅ Próximos eventos
- ✅ Próximas citas
- ✅ Notificaciones recientes
- ✅ Calendario de eventos
- ✅ Onboarding para usuarios nuevos

#### **Membresías**
- ✅ 4 Planes disponibles:
  - **Básico**: Gratis
  - **Pro**: $60/año
  - **Premium**: $120/año
  - **DeLuxe**: $200/año
- ✅ Compra de membresías
- ✅ Renovación automática
- ✅ Visualización de beneficios por plan

#### **Carrito de Compras**
- ✅ Agregar múltiples productos
- ✅ Membresías, eventos, servicios
- ✅ Aplicar códigos de descuento
- ✅ Descuento maestro automático
- ✅ Cálculo de totales con descuentos
- ✅ Checkout integrado

#### **Eventos**
- ✅ Listado de eventos públicos
- ✅ Registro a eventos
- ✅ Información detallada
- ✅ Galería de imágenes
- ✅ Certificados
- ✅ Kahoot integrado

#### **Citas/Appointments**
- ✅ Solicitar citas con asesores
- ✅ Selección de tipo de cita
- ✅ Selección de horario disponible
- ✅ Confirmación y recordatorios
- ✅ Historial de citas

#### **Beneficios y Servicios**
- ✅ Visualización de beneficios por membresía
- ✅ Servicios disponibles
- ✅ Solicitud de Office 365

#### **Notificaciones**
- ✅ Notificaciones en tiempo real
- ✅ Configuración de preferencias
- ✅ Historial de notificaciones

### 🔧 **Para Administradores**

#### **Panel de Administración**
- ✅ Dashboard con estadísticas
- ✅ Gestión completa de usuarios
- ✅ Gestión de membresías
- ✅ Gestión de eventos
- ✅ Gestión de citas
- ✅ Configuración de pagos
- ✅ Gestión de notificaciones
- ✅ Historial de emails

#### **Gestión de Usuarios**
- ✅ Listado con filtros avanzados
- ✅ Búsqueda por nombre, email, teléfono
- ✅ Filtros por estado, rol, grupo, etiquetas
- ✅ Crear, editar, eliminar usuarios
- ✅ Asignar roles (admin, asesor)
- ✅ Gestión de grupos y etiquetas
- ✅ Activar/desactivar usuarios

#### **Gestión de Membresías**
- ✅ Ver todas las membresías
- ✅ Estados y fechas
- ✅ Renovaciones
- ✅ Historial de pagos

#### **Gestión de Eventos**
- ✅ CRUD completo de eventos
- ✅ Flujo de 5 pasos
- ✅ Asignación de roles (moderador, administrador, expositor)
- ✅ Gestión de imágenes
- ✅ Configuración de precios y descuentos
- ✅ Control de capacidad
- ✅ Publicación/archivado

#### **Gestión de Citas**
- ✅ Ver todas las citas
- ✅ Asignar asesores
- ✅ Gestionar disponibilidad
- ✅ Configurar tipos de citas
- ✅ Configurar precios

#### **Sistema de Descuentos**
- ✅ Gestión de descuentos por membresía
- ✅ **Códigos de descuento promocionales**
  - Generación manual o automática
  - Configuración de alcance (todo, eventos, membresías, citas)
  - Límites de uso (total y por usuario)
  - Fechas de vigencia
  - Historial de aplicaciones
- ✅ **Descuento Maestro**
  - Descuento global automático
  - Configuración desde panel admin
  - Aplicación automática en checkout

#### **Configuración de Pagos**
- ✅ Múltiples métodos:
  - Stripe (tarjetas de crédito)
  - PayPal
  - Banco General (CyberSource)
  - Yappy (Panamá)
  - Interbank (Perú)
- ✅ Configuración desde BD o variables de entorno
- ✅ Modo demo para pruebas
- ✅ Credenciales seguras

#### **Sistema de Email**
- ✅ Configuración de SMTP
- ✅ Plantillas personalizables
- ✅ Historial completo de emails
- ✅ Reenvío de emails fallidos
- ✅ Diagnóstico de problemas
- ✅ Estadísticas de envío

#### **Sistema de Notificaciones**
- ✅ Configuración de tipos de notificaciones
- ✅ Activar/desactivar por tipo
- ✅ Gestión de preferencias
- ✅ Historial completo

#### **Multimedia y Ayuda**
- ✅ Configuración de videos y audios
- ✅ Guías visuales interactivas
- ✅ Procedimientos paso a paso
- ✅ Sección de ayuda completa

---

## 💳 Sistema de Pagos

### **Métodos Soportados**
1. **Stripe** - Tarjetas de crédito/débito
   - Integración completa con API
   - Modo demo incluido
   - Webhooks para confirmación

2. **PayPal** - Pagos mediante PayPal
   - Integración con API de PayPal
   - Flujo de retorno y cancelación

3. **Banco General** - CyberSource
   - Integración con API de CyberSource
   - Pagos manuales con referencia

4. **Yappy** - Pagos móviles (Panamá)
   - Generación de referencias
   - Pagos manuales

5. **Interbank** - Transferencias bancarias (Perú)
   - Información de cuenta
   - Pagos manuales

### **Características**
- ✅ Configuración desde panel administrativo
- ✅ Credenciales en BD o variables de entorno
- ✅ Modo demo para pruebas
- ✅ Múltiples métodos en un solo checkout
- ✅ Procesamiento modular (payment_processors.py)
- ✅ Historial completo de pagos
- ✅ Estados de pago (pending, succeeded, failed)
- ✅ Metadata y referencias
- ✅ Comprobantes y URLs de pago

---

## 🎫 Sistema de Descuentos

### **Tipos de Descuentos**

1. **Descuentos por Membresía** (Discount)
   - Aplicación automática según tipo de membresía
   - Vinculados a eventos específicos
   - Por categoría (evento, cita, servicio)
   - Prioridad de aplicación

2. **Descuento Maestro** (Discount.is_master)
   - Descuento global automático
   - Se aplica a todo el carrito
   - Configurable desde panel admin
   - Prioridad sobre códigos promocionales

3. **Códigos Promocionales** (DiscountCode)
   - Generación manual o automática
   - Códigos únicos
   - Tipos: porcentaje o fijo
   - Alcance configurable:
     - Todo el sistema
     - Solo eventos
     - Solo membresías
     - Solo citas
   - Límites de uso (total y por usuario)
   - Fechas de vigencia
   - Historial de aplicaciones

### **Orden de Aplicación**
1. Precio base del item
2. Descuento por membresía (automático)
3. Subtotal del carrito
4. Descuento maestro (automático)
5. Código promocional (manual)
6. Total final

---

## 📧 Sistema de Notificaciones y Email

### **Tipos de Notificaciones**
- Membresía (pago, renovación, expiración)
- Eventos (registro, actualización, cancelación)
- Citas (confirmación, recordatorio, cancelación)
- Pagos (confirmación, fallido)
- Sistema (bienvenida, verificación de email)

### **Características**
- ✅ Envío automático de emails
- ✅ Plantillas personalizables
- ✅ Historial completo (EmailLog)
- ✅ Reintentos automáticos
- ✅ Diagnóstico de problemas
- ✅ Configuración de SMTP desde BD
- ✅ Preferencias de usuario
- ✅ Notificaciones en dashboard

---

## 🎉 Sistema de Eventos

### **Características**
- ✅ Flujo de 5 pasos:
  1. Evento (información básica)
  2. Descripción (detalles)
  3. Publicidad (marketing)
  4. Certificado (generación)
  5. Kahoot (interactividad)
- ✅ Roles múltiples:
  - Creador
  - Moderador
  - Administrador
  - Expositor/Conferencista
- ✅ Galería de imágenes
- ✅ Precios y descuentos por membresía
- ✅ Capacidad y registro
- ✅ Estados: draft, published, archived
- ✅ Talleres y temas
- ✅ Certificados
- ✅ Integración con Kahoot

---

## 📅 Sistema de Citas

### **Características**
- ✅ Tipos de citas configurables
- ✅ Asesores con disponibilidad
- ✅ Horarios disponibles (slots)
- ✅ Precios por tipo de membresía
- ✅ Confirmación y recordatorios
- ✅ Múltiples participantes
- ✅ Estados: pending, confirmed, completed, cancelled
- ✅ Notas y comentarios

---

## 🛒 Carrito de Compras

### **Características**
- ✅ Un carrito por usuario
- ✅ Múltiples productos:
  - Membresías
  - Eventos
  - Servicios
- ✅ Aplicación de descuentos:
  - Descuento maestro (automático)
  - Códigos promocionales (manual)
- ✅ Cálculo de totales con descuentos
- ✅ Checkout integrado
- ✅ Procesamiento después del pago

---

## 🔐 Seguridad

- ✅ Autenticación con Flask-Login
- ✅ Contraseñas hasheadas (Werkzeug)
- ✅ Verificación de email obligatoria
- ✅ Tokens de verificación con expiración
- ✅ Protección CSRF
- ✅ Variables de entorno para claves
- ✅ Decoradores de autorización (@admin_required)
- ✅ Validación de formularios
- ✅ Sanitización de inputs
- ✅ Logs de actividad

---

## 📊 Estadísticas y Reportes

- ✅ Dashboard administrativo con métricas
- ✅ Total de usuarios
- ✅ Membresías activas
- ✅ Pagos exitosos
- ✅ Ingresos totales
- ✅ Estadísticas de emails
- ✅ Estadísticas de notificaciones
- ✅ Uso de códigos de descuento

---

## 🎨 Interfaz de Usuario

### **Tecnologías Frontend**
- Bootstrap 5
- Font Awesome 6
- JavaScript vanilla
- CSS personalizado con paleta RelaticPanama

### **Características UI**
- ✅ Diseño responsive
- ✅ Paleta de colores oficial
- ✅ Logo SVG personalizado
- ✅ Menú lateral colapsable
- ✅ Modales y alertas
- ✅ Formularios validados
- ✅ Tablas con paginación
- ✅ Filtros avanzados
- ✅ Búsqueda en tiempo real

---

## 🔌 Integraciones

### **APIs Externas**
- Stripe API (pagos)
- PayPal API (pagos)
- CyberSource API (Banco General)
- Yappy API (pagos móviles)
- Office 365 SMTP (emails)
- Gmail SMTP (emails alternativo)

### **Módulos Internos**
- Sistema de licencias (validación)
- Email service (envío de emails)
- Payment processors (procesamiento de pagos)
- Notification engine (motor de notificaciones)
- Event routes (gestión de eventos)
- Appointment routes (gestión de citas)

---

## 📁 Estructura del Proyecto

```
membresia-relatic/
├── backend/
│   ├── app.py                    # Aplicación Flask principal
│   ├── payment_processors.py     # Procesadores de pago
│   ├── email_service.py          # Servicio de email
│   ├── email_templates.py        # Plantillas de email
│   ├── event_routes.py           # Rutas de eventos
│   ├── appointment_routes.py     # Rutas de citas
│   └── migrate_*.py              # Scripts de migración
├── templates/
│   ├── admin/                    # Templates administrativos
│   ├── events/                   # Templates de eventos
│   ├── appointments/             # Templates de citas
│   ├── emails/                   # Templates de email
│   └── *.html                    # Templates principales
├── static/
│   ├── css/                      # Estilos
│   ├── js/                       # JavaScript
│   └── images/                   # Imágenes y logos
├── docs/                         # Documentación
└── requirements.txt              # Dependencias
```

---

## 🚀 Tecnologías Utilizadas

### **Backend**
- Python 3.12
- Flask (Framework web)
- SQLAlchemy (ORM)
- Flask-Login (Autenticación)
- Flask-Mail (Emails)
- Werkzeug (Seguridad)

### **Base de Datos**
- SQLite (desarrollo)
- PostgreSQL (producción compatible)

### **Frontend**
- Bootstrap 5
- Font Awesome 6
- JavaScript ES6+
- HTML5/CSS3

### **APIs y Servicios**
- Stripe API
- PayPal API
- CyberSource API
- Office 365 SMTP
- Gmail SMTP

---

## 📈 Métricas del Sistema

- **34 Modelos** de base de datos
- **78+ Rutas** de aplicación
- **Múltiples métodos de pago** (5)
- **Sistema de descuentos** completo
- **Sistema de eventos** con flujo de 5 pasos
- **Sistema de citas** completo
- **Sistema de notificaciones** robusto
- **Panel administrativo** completo
- **Sistema de email** configurable
- **Carrito de compras** avanzado

---

## 🎯 Casos de Uso Principales

1. **Usuario se registra** → Verifica email → Compra membresía → Accede a beneficios
2. **Usuario navega eventos** → Se registra → Recibe confirmación → Asiste → Obtiene certificado
3. **Usuario solicita cita** → Selecciona asesor y horario → Confirma → Asiste
4. **Administrador crea evento** → Configura precios → Publica → Gestiona registros
5. **Administrador crea código descuento** → Usuario lo aplica → Obtiene descuento
6. **Sistema envía notificaciones** → Email automático → Registro en log → Usuario recibe

---

## 🔄 Flujos Principales

### **Flujo de Compra**
1. Usuario selecciona membresía/producto
2. Se agrega al carrito
3. Sistema aplica descuento maestro (si existe)
4. Usuario introduce código promocional (opcional)
5. Checkout con método de pago
6. Procesamiento de pago
7. Confirmación y activación
8. Email de confirmación

### **Flujo de Evento**
1. Admin crea evento (5 pasos)
2. Configura precios y descuentos
3. Publica evento
4. Usuarios se registran
5. Sistema aplica descuentos por membresía
6. Confirmación y recordatorios
7. Check-in en el evento
8. Generación de certificado

### **Flujo de Cita**
1. Usuario solicita cita
2. Selecciona tipo y asesor
3. Elige horario disponible
4. Sistema confirma
5. Recordatorio automático
6. Cita se realiza
7. Sistema marca como completada

---

## 📝 Notas Importantes

- El sistema es **modular** y **escalable**
- Soporta **múltiples métodos de pago** simultáneos
- Sistema de **descuentos en cascada** (membresía → maestro → código)
- **Compatible** con el sistema anterior de membresías
- **Modo demo** para pruebas sin credenciales reales
- **Configuración flexible** (BD o variables de entorno)
- **Logs completos** para auditoría
- **Sistema de ayuda** integrado con guías visuales

---

**Versión del Documento**: 1.0  
**Última Actualización**: Diciembre 2025  
**Sistema**: Membresía RelaticPanama

