# Protocolo de Pruebas - Sistema nodeone

> **Propósito**: Documento que define cómo probar todos los módulos y funcionalidades del sistema de manera sistemática.

---

## 📋 Índice

1. [Pruebas de Usuarios y Autenticación](#1-pruebas-de-usuarios-y-autenticación)
2. [Pruebas de Membresías y Pagos](#2-pruebas-de-membresías-y-pagos)
3. [Pruebas de Eventos](#3-pruebas-de-eventos)
4. [Pruebas de Citas (Appointments)](#4-pruebas-de-citas-appointments)
5. [Pruebas del Sistema de Emails](#5-pruebas-del-sistema-de-emails)
6. [Pruebas de Notificaciones](#6-pruebas-de-notificaciones)
7. [Pruebas del Carrito de Compras](#7-pruebas-del-carrito-de-compras)
8. [Pruebas del Panel de Administración](#8-pruebas-del-panel-de-administración)
9. [Pruebas de APIs](#9-pruebas-de-apis)
10. [Pruebas de Seguridad](#10-pruebas-de-seguridad)
11. [Pruebas de Integración](#11-pruebas-de-integración)

---

## 1. Pruebas de Usuarios y Autenticación

### 1.1 Registro de Usuario

**Pasos:**
1. Ir a `/register`
2. Completar formulario con datos válidos
3. Verificar que se valide el formato de email
4. Verificar que se bloquee email duplicado
5. Verificar que se bloquee dominio temporal (tempmail, etc.)

**Resultados esperados:**
- ✅ Usuario creado con `email_verified=False`
- ✅ Token de verificación generado
- ✅ Email de verificación enviado
- ✅ Email de bienvenida enviado (si está habilitado)
- ✅ Redirección a `/login` con mensaje de éxito

**Casos de prueba:**
- Email válido → ✅ Debe funcionar
- Email duplicado → ❌ Error "El correo electrónico ya está registrado"
- Email con dominio temporal → ❌ Error "No se permiten direcciones de correo temporal"
- Email con formato inválido → ❌ Error de validación
- Campos vacíos → ❌ Error "Todos los campos obligatorios deben ser completados"

### 1.2 Verificación de Email

**Pasos:**
1. Registrarse como nuevo usuario
2. Revisar email recibido
3. Hacer clic en enlace de verificación
4. Verificar que `email_verified=True`

**Resultados esperados:**
- ✅ Email de verificación recibido
- ✅ Enlace funciona y verifica el email
- ✅ Usuario puede acceder a funciones que requieren verificación

**Casos de prueba:**
- Token válido → ✅ Email verificado
- Token expirado (24h) → ❌ Error "El enlace de verificación ha expirado"
- Token inválido → ❌ Error "El enlace de verificación no es válido"
- Reenviar verificación → ✅ Nuevo token generado, anterior invalidado

### 1.3 Login

**Pasos:**
1. Ir a `/login`
2. Ingresar credenciales válidas
3. Verificar inicio de sesión

**Resultados esperados:**
- ✅ Usuario autenticado
- ✅ Redirección a `/dashboard`
- ✅ Sesión activa

**Casos de prueba:**
- Credenciales válidas → ✅ Login exitoso
- Email incorrecto → ❌ Error "Credenciales inválidas"
- Contraseña incorrecta → ❌ Error "Credenciales inválidas"
- Usuario inactivo → ❌ Error "Credenciales inválidas"

### 1.4 Logout

**Pasos:**
1. Estar autenticado
2. Ir a `/logout`
3. Verificar cierre de sesión

**Resultados esperados:**
- ✅ Sesión cerrada
- ✅ Redirección a página principal
- ✅ No se puede acceder a rutas protegidas

---

## 2. Pruebas de Membresías y Pagos

### 2.1 Compra de Membresía

**Pasos:**
1. Login como usuario verificado
2. Ir a `/membership`
3. Seleccionar tipo de membresía (pro, premium, deluxe)
4. Agregar al carrito
5. Ir a checkout
6. Completar pago (modo demo o Stripe real)

**Resultados esperados:**
- ✅ Membresía agregada al carrito
- ✅ Checkout muestra precio correcto
- ✅ Pago procesado exitosamente
- ✅ Subscription creada con `status='active'`
- ✅ Email de confirmación enviado
- ✅ Notificación creada en panel

**Casos de prueba:**
- Membresía Pro ($60) → ✅ Precio correcto
- Membresía Premium ($120) → ✅ Precio correcto
- Membresía Deluxe ($200) → ✅ Precio correcto
- Usuario sin email verificado → ❌ No puede hacer checkout
- Pago fallido → ❌ Payment con `status='failed'`, no se crea subscription

### 2.2 Renovación de Membresía

**Pasos:**
1. Usuario con membresía activa
2. Antes de expirar, renovar membresía
3. Completar pago

**Resultados esperados:**
- ✅ Nueva subscription creada
- ✅ Fecha de inicio y fin correctas (1 año)
- ✅ Email de renovación enviado

### 2.3 Verificación de Membresía Activa

**Pasos:**
1. Usuario con membresía activa
2. Verificar en dashboard que se muestra correctamente
3. Verificar acceso a beneficios

**Resultados esperados:**
- ✅ Dashboard muestra membresía activa
- ✅ Días restantes calculados correctamente
- ✅ Acceso a beneficios según tipo de membresía

---

## 3. Pruebas de Eventos

### 3.1 Crear Evento (Admin)

**Pasos:**
1. Login como admin
2. Ir a `/admin/events/create`
3. Completar formulario de evento
4. Guardar

**Resultados esperados:**
- ✅ Evento creado con `publish_status='draft'`
- ✅ Slug generado automáticamente
- ✅ Roles asignados (moderador, admin, expositor)

**Casos de prueba:**
- Evento con todos los campos → ✅ Creado correctamente
- Evento sin fecha → ❌ Error de validación
- Slug duplicado → ❌ Error de validación

### 3.2 Publicar Evento

**Pasos:**
1. Evento en estado 'draft'
2. Cambiar a `publish_status='published'`
3. Verificar visibilidad

**Resultados esperados:**
- ✅ Evento visible para miembros
- ✅ Aparece en lista de eventos públicos

### 3.3 Registro a Evento

**Pasos:**
1. Usuario verificado
2. Ver evento publicado
3. Registrarse al evento
4. Completar pago si es necesario

**Resultados esperados:**
- ✅ EventRegistration creado
- ✅ Precio calculado según membresía (descuentos aplicados)
- ✅ Email de confirmación al usuario
- ✅ Notificaciones a responsables (moderador, admin, expositor)
- ✅ Contador `registered_count` incrementado

**Casos de prueba:**
- Usuario Basic → ✅ Precio base (sin descuento)
- Usuario Pro → ✅ 10% descuento
- Usuario Premium → ✅ 20% descuento
- Usuario Deluxe → ✅ 30% descuento
- Evento sin capacidad → ✅ Registro permitido
- Evento con capacidad llena → ❌ Error "Evento lleno"

### 3.4 Cancelación de Registro

**Pasos:**
1. Usuario registrado en evento
2. Cancelar registro
3. Verificar notificaciones

**Resultados esperados:**
- ✅ EventRegistration con `status='cancelled'`
- ✅ Email de cancelación al usuario
- ✅ Notificaciones a responsables
- ✅ Contador `registered_count` decrementado

---

## 4. Pruebas de Citas (Appointments)

### 4.1 Crear Tipo de Cita (Admin)

**Pasos:**
1. Login como admin
2. Crear AppointmentType
3. Configurar precios por membresía

**Resultados esperados:**
- ✅ AppointmentType creado
- ✅ Reglas de precio configuradas
- ✅ Asesores asignados

### 4.2 Configurar Disponibilidad de Asesor

**Pasos:**
1. Asesor configurado
2. Definir horarios disponibles (AdvisorAvailability)
3. Verificar slots generados

**Resultados esperados:**
- ✅ Disponibilidad guardada
- ✅ Slots generados automáticamente
- ✅ Slots visibles para reserva

### 4.3 Reservar Cita

**Pasos:**
1. Usuario verificado
2. Seleccionar tipo de cita
3. Seleccionar asesor
4. Seleccionar slot disponible
5. Completar reserva

**Resultados esperados:**
- ✅ Appointment creado con `status='pending'`
- ✅ Precio calculado según membresía
- ✅ Slot marcado como reservado
- ✅ Email de confirmación pendiente al usuario
- ✅ Notificación al asesor

**Casos de prueba:**
- Cita incluida en membresía Premium → ✅ Precio $0
- Cita con descuento Pro → ✅ Descuento aplicado
- Slot ya reservado → ❌ Error "Slot no disponible"
- Cita grupal → ✅ Múltiples participantes permitidos

### 4.4 Confirmar Cita (Asesor)

**Pasos:**
1. Asesor ve cita pendiente
2. Confirmar cita
3. Verificar notificaciones

**Resultados esperados:**
- ✅ Appointment con `status='confirmed'`
- ✅ `advisor_confirmed=True`
- ✅ Email de confirmación al usuario
- ✅ Link de reunión generado (si es virtual)

### 4.5 Cancelar Cita

**Pasos:**
1. Usuario o asesor cancela cita
2. Verificar liberación de slot

**Resultados esperados:**
- ✅ Appointment con `status='cancelled'`
- ✅ Slot liberado (disponible nuevamente)
- ✅ Email de cancelación enviado
- ✅ Razón de cancelación registrada

---

## 5. Pruebas del Sistema de Emails

### 5.1 Configuración SMTP

**Pasos:**
1. Login como admin
2. Ir a `/admin/email`
3. Configurar servidor SMTP
4. Probar envío

**Resultados esperados:**
- ✅ Configuración guardada en EmailConfig
- ✅ Configuración aplicada a Flask-Mail
- ✅ Email de prueba enviado exitosamente
- ✅ Email registrado en EmailLog

**Casos de prueba:**
- Gmail con App Password → ✅ Funciona
- Office 365 → ✅ Funciona
- Credenciales incorrectas → ❌ Error de autenticación
- Variables de entorno → ✅ Usa credenciales de entorno

### 5.2 Envío de Email de Bienvenida

**Pasos:**
1. Registrar nuevo usuario
2. Verificar email recibido
3. Verificar en EmailLog

**Resultados esperados:**
- ✅ Email recibido
- ✅ Template HTML correcto
- ✅ Logo visible (si existe)
- ✅ Registrado en EmailLog con `status='sent'`
- ✅ Notification creada con `email_sent=True`

### 5.3 Reintentos Automáticos

**Pasos:**
1. Configurar SMTP incorrecto temporalmente
2. Intentar enviar email
3. Corregir configuración
4. Verificar reintentos

**Resultados esperados:**
- ✅ 3 intentos realizados
- ✅ Backoff exponencial (2s, 4s, 8s)
- ✅ Registrado en EmailLog con `status='failed'`
- ✅ `retry_count` registrado
- ✅ `error_message` guardado

### 5.4 Reenvío de Email Fallido

**Pasos:**
1. Login como admin
2. Ir a `/admin/messaging`
3. Buscar email con `status='failed'`
4. Hacer clic en "Reenviar"

**Resultados esperados:**
- ✅ Email reenviado exitosamente
- ✅ Status actualizado a 'sent'
- ✅ `retry_count` incrementado
- ✅ `sent_at` actualizado

### 5.5 Templates de Email

**Pasos:**
1. Login como admin
2. Ir a `/admin/email` (pestaña Templates)
3. Editar template
4. Preview del template
5. Resetear a versión por defecto

**Resultados esperados:**
- ✅ Templates listados por categoría
- ✅ Edición guardada correctamente
- ✅ Preview muestra HTML correcto
- ✅ Reset restaura template por defecto

---

## 6. Pruebas de Notificaciones

### 6.1 Configuración de Notificaciones

**Pasos:**
1. Login como admin
2. Ir a `/admin/notifications`
3. Deshabilitar una notificación
4. Verificar que no se envía

**Resultados esperados:**
- ✅ Configuración guardada
- ✅ Notificación deshabilitada no se envía
- ✅ Mensaje en consola indicando deshabilitación

**Casos de prueba:**
- Deshabilitar "welcome" → ✅ No se envía email de bienvenida
- Deshabilitar "membership_payment" → ✅ No se envía confirmación de pago
- Habilitar todas → ✅ Todas las notificaciones funcionan

### 6.2 Notificaciones en Panel

**Pasos:**
1. Usuario autenticado
2. Ir a `/notifications`
3. Ver notificaciones
4. Marcar como leída
5. Eliminar notificación

**Resultados esperados:**
- ✅ Lista de notificaciones mostrada
- ✅ Contador de no leídas correcto
- ✅ Marcar como leída funciona
- ✅ Eliminar funciona

### 6.3 Tipos de Notificaciones

**Verificar que cada tipo funciona:**

1. **welcome** - Al registrarse
2. **membership_payment** - Al pagar membresía
3. **membership_expiring** - 30, 15, 7, 1 días antes
4. **membership_expired** - Al expirar
5. **membership_renewed** - Al renovar
6. **event_registration** - Al registrarse a evento
7. **event_registration_user** - Confirmación al usuario
8. **event_cancellation** - Al cancelar registro
9. **event_confirmation** - Al confirmar registro
10. **event_update** - Al actualizar evento
11. **appointment_confirmation** - Al confirmar cita
12. **appointment_reminder** - 24 y 48h antes

**Resultados esperados:**
- ✅ Cada tipo crea Notification en BD
- ✅ Email enviado si está habilitado
- ✅ `email_sent=True` si se envió
- ✅ Registrado en EmailLog

---

## 7. Pruebas del Carrito de Compras

### 7.1 Agregar Producto al Carrito

**Pasos:**
1. Usuario autenticado
2. Agregar membresía al carrito
3. Agregar evento al carrito
4. Verificar carrito

**Resultados esperados:**
- ✅ Productos agregados correctamente
- ✅ Precios correctos
- ✅ Cantidad actualizable
- ✅ Total calculado correctamente

**Casos de prueba:**
- Agregar membresía → ✅ Agregada
- Agregar mismo producto → ✅ Cantidad incrementada
- Agregar evento → ✅ Precio con descuento según membresía
- Usuario sin email verificado → ❌ No puede agregar

### 7.2 Eliminar del Carrito

**Pasos:**
1. Carrito con productos
2. Eliminar item
3. Verificar actualización

**Resultados esperados:**
- ✅ Item eliminado
- ✅ Total actualizado
- ✅ Contador actualizado

### 7.3 Checkout desde Carrito

**Pasos:**
1. Carrito con productos
2. Ir a checkout
3. Completar pago

**Resultados esperados:**
- ✅ Checkout muestra todos los items
- ✅ Total correcto
- ✅ Pago procesado
- ✅ Carrito vaciado después del pago
- ✅ Subscriptions/Registrations creados según productos

---

## 8. Pruebas del Panel de Administración

### 8.1 Gestión de Usuarios

**Pasos:**
1. Login como admin
2. Ir a `/admin/users`
3. Buscar usuario
4. Editar usuario
5. Crear usuario
6. Eliminar usuario

**Resultados esperados:**
- ✅ Lista de usuarios con paginación
- ✅ Filtros funcionan (activo, admin, asesor, grupo, tags)
- ✅ Búsqueda funciona
- ✅ Edición guardada
- ✅ Usuario creado
- ✅ Usuario eliminado (excepto propio)

**Casos de prueba:**
- Crear usuario como admin → ✅ Creado con permisos
- Crear usuario como asesor → ✅ Perfil Advisor creado
- Eliminar usuario propio → ❌ Error "No puedes eliminar tu propio usuario"

### 8.2 Gestión de Membresías

**Pasos:**
1. Ir a `/admin/memberships`
2. Ver lista de membresías
3. Verificar estados

**Resultados esperados:**
- ✅ Lista de membresías mostrada
- ✅ Estados correctos (activa, expirada)
- ✅ Fechas correctas

### 8.3 Gestión de Emails

**Pasos:**
1. Ir a `/admin/messaging`
2. Ver lista de emails
3. Filtrar por tipo/estado
4. Ver detalle de email
5. Reenviar email fallido

**Resultados esperados:**
- ✅ Lista paginada de emails
- ✅ Filtros funcionan
- ✅ Búsqueda funciona
- ✅ Detalle muestra contenido completo
- ✅ Reenvío funciona

### 8.4 Estadísticas

**Pasos:**
1. Ir a `/admin`
2. Verificar estadísticas mostradas

**Resultados esperados:**
- ✅ Total de usuarios correcto
- ✅ Total de membresías correcto
- ✅ Membresías activas correctas
- ✅ Total de pagos correcto
- ✅ Ingresos totales correctos

---

## 9. Pruebas de APIs

### 9.1 API de Membresía

**Endpoint:** `GET /api/user/membership`

**Pasos:**
1. Usuario autenticado
2. Hacer request a API
3. Verificar respuesta JSON

**Resultados esperados:**
- ✅ JSON con información de membresía
- ✅ 404 si no tiene membresía activa

### 9.2 API de Notificaciones

**Endpoints:**
- `GET /api/notifications`
- `POST /api/notifications/<id>/read`
- `POST /api/notifications/read-all`
- `DELETE /api/notifications/<id>`

**Pasos:**
1. Usuario autenticado
2. Hacer requests a cada endpoint
3. Verificar respuestas

**Resultados esperados:**
- ✅ Lista de notificaciones con filtros
- ✅ Marcar como leída funciona
- ✅ Marcar todas como leídas funciona
- ✅ Eliminar funciona

### 9.3 API de Estadísticas de Emails

**Endpoint:** `GET /api/admin/messaging/stats`

**Pasos:**
1. Login como admin
2. Hacer request
3. Verificar JSON

**Resultados esperados:**
- ✅ JSON con estadísticas
- ✅ Total, enviados, fallidos
- ✅ Estadísticas por tipo
- ✅ Estadísticas por día (últimos 30 días)

---

## 10. Pruebas de Seguridad

### 10.1 Rutas Protegidas

**Verificar:**
- Rutas con `@login_required` → ❌ Redirigen a login si no autenticado
- Rutas con `@admin_required` → ❌ Redirigen si no es admin
- Rutas con `@email_verified_required` → ❌ Redirigen si email no verificado

### 10.2 Validación de Email

**Casos de prueba:**
- Email válido → ✅ Aceptado
- Email con dominio temporal → ❌ Rechazado
- Email con formato inválido → ❌ Rechazado
- Email demasiado largo → ❌ Rechazado

### 10.3 Protección CSRF

**Verificar:**
- Formularios tienen protección CSRF
- Requests POST requieren token válido

### 10.4 Contraseñas

**Verificar:**
- Contraseñas hasheadas (no en texto plano)
- Verificación de contraseña funciona
- Cambio de contraseña requiere contraseña actual

---

## 11. Pruebas de Integración

### 11.1 Flujo Completo: Registro → Membresía → Evento

**Pasos:**
1. Registrar nuevo usuario
2. Verificar email
3. Comprar membresía
4. Registrarse a evento
5. Verificar notificaciones y emails

**Resultados esperados:**
- ✅ Todo el flujo funciona sin errores
- ✅ Todos los emails enviados
- ✅ Todas las notificaciones creadas
- ✅ Datos consistentes en BD

### 11.2 Flujo Completo: Cita

**Pasos:**
1. Admin crea AppointmentType
2. Asesor configura disponibilidad
3. Usuario reserva cita
4. Asesor confirma
5. Verificar notificaciones

**Resultados esperados:**
- ✅ Flujo completo funciona
- ✅ Slots generados correctamente
- ✅ Precios calculados según membresía
- ✅ Notificaciones enviadas

### 11.3 Integración Stripe (si está configurado)

**Pasos:**
1. Configurar Stripe real (no demo)
2. Hacer pago de prueba
3. Verificar webhook
4. Verificar subscription creada

**Resultados esperados:**
- ✅ Payment Intent creado
- ✅ Webhook procesado
- ✅ Payment actualizado a 'succeeded'
- ✅ Subscription creada automáticamente

---

## 📊 Checklist de Pruebas

### Pruebas Críticas (Deben pasar siempre)

- [ ] Registro de usuario funciona
- [ ] Verificación de email funciona
- [ ] Login funciona
- [ ] Compra de membresía funciona
- [ ] Envío de emails funciona
- [ ] Notificaciones se crean correctamente
- [ ] Panel admin accesible solo para admins

### Pruebas Importantes

- [ ] Registro a eventos funciona
- [ ] Reserva de citas funciona
- [ ] Carrito de compras funciona
- [ ] Descuentos por membresía aplicados correctamente
- [ ] Reintentos de email funcionan

### Pruebas de Validación

- [ ] Validación de email funciona
- [ ] Validación de formularios funciona
- [ ] Protección de rutas funciona
- [ ] Manejo de errores funciona

---

## 🔧 Herramientas de Prueba

### Comandos Útiles

```bash
# Ver logs del servicio
sudo journalctl -u nodeone.service -f

# Verificar estado del servicio
sudo systemctl status nodeone.service

# Reiniciar servicio
sudo systemctl restart nodeone.service

# Ver base de datos
sqlite3 backend/instance/membership_legacy.db
```

### Consultas SQL Útiles

```sql
-- Ver usuarios
SELECT id, email, first_name, last_name, email_verified, is_admin FROM user;

-- Ver membresías activas
SELECT * FROM subscription WHERE status = 'active' AND end_date > datetime('now');

-- Ver emails enviados
SELECT recipient_email, subject, status, sent_at FROM email_log ORDER BY created_at DESC LIMIT 10;

-- Ver emails fallidos
SELECT recipient_email, subject, error_message FROM email_log WHERE status = 'failed';

-- Ver notificaciones
SELECT notification_type, COUNT(*) FROM notification GROUP BY notification_type;
```

---

## 📝 Notas de Pruebas

1. **Modo Demo**: El sistema tiene modo demo para pagos (no requiere Stripe real)
2. **Emails**: Verificar que la configuración SMTP esté correcta antes de probar
3. **Notificaciones**: Verificar que estén habilitadas en `/admin/notifications`
4. **Base de Datos**: Hacer backup antes de pruebas extensivas
5. **Logs**: Revisar logs del servidor para errores

---

**Última actualización**: 2025-01-XX
**Versión del protocolo**: 1.0.0

