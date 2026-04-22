# Análisis del Sistema de Citas - Easy NodeOne

## 📋 Resumen Ejecutivo

Este documento analiza los requisitos para implementar un sistema de citas (appointments) separado de los eventos, inspirado en Odoo pero adaptado a las necesidades específicas de Easy NodeOne.

---

## 🎯 Diferencias Clave: Eventos vs Citas

### **EVENTOS** (Ya implementado)
- **Naturaleza**: Actividades masivas con fecha específica
- **Ejemplos**: Congresos, talleres, webinars, seminarios, simposios, ferias
- **Características**:
  - Fecha y hora fijas
  - Registro obligatorio para todos
  - Formularios específicos por evento
  - Múltiples participantes
  - Costos con descuentos por membresía
  - Capacidad limitada
  - Expositores, agenda, materiales

### **CITAS** (Por implementar)
- **Naturaleza**: Reservas de tiempo individuales o grupales
- **Ejemplos**: Asesoría en revisión de artículos, consultoría, asesoría en publicaciones
- **Características**:
  - Horarios flexibles según disponibilidad del asesor
  - Reserva de slots de tiempo
  - Individual o grupal (virtual)
  - Costos variables según membresía
  - Confirmación por asesor
  - Notificaciones por correo y panel

---

## 🏗️ Arquitectura Propuesta

### 1. **Modelo: AppointmentType (Tipo de Cita/Servicio)**
Define los servicios que pueden ser reservados como citas.

```python
class AppointmentType(db.Model):
    """Tipos de citas disponibles (servicios configurables)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # "Asesoría en Revisión de Artículos"
    description = db.Column(db.Text)
    service_category = db.Column(db.String(100))  # Relacionado con Benefit
    duration_minutes = db.Column(db.Integer, nullable=False)  # 30, 60, 90 minutos
    is_group_allowed = db.Column(db.Boolean, default=False)  # Permite grupos
    max_participants = db.Column(db.Integer, default=1)
    base_price = db.Column(db.Float, default=0.0)  # Precio base
    currency = db.Column(db.String(3), default='USD')
    is_virtual = db.Column(db.Boolean, default=True)
    requires_confirmation = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    advisors = db.relationship('AppointmentAdvisor', backref='appointment_type', lazy=True)
    appointments = db.relationship('Appointment', backref='appointment_type', lazy=True)
    pricing_rules = db.relationship('AppointmentPricing', backref='appointment_type', lazy=True)
```

### 2. **Modelo: Advisor (Asesor)**
Los profesionales que ofrecen las citas.

```python
class Advisor(db.Model):
    """Asesores que ofrecen citas"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Usuarios locales ascendidos a rol asesor
    specializations = db.Column(db.Text)  # Áreas de especialización
    bio = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='advisor_profile')
    availability = db.relationship('AdvisorAvailability', backref='advisor', lazy=True)
    appointments = db.relationship('Appointment', backref='advisor', lazy=True)
```

### 3. **Modelo: AdvisorAvailability (Disponibilidad)**
Horarios disponibles de cada asesor.

```python
class AdvisorAvailability(db.Model):
    """Disponibilidad semanal de los asesores"""
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunes, 6=Domingo
    start_time = db.Column(db.Time, nullable=False)  # "08:00"
    end_time = db.Column(db.Time, nullable=False)    # "12:00"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 4. **Modelo: AppointmentSlot (Slots Disponibles)**
Slots generados automáticamente basados en disponibilidad.

```python
class AppointmentSlot(db.Model):
    """Slots de tiempo disponibles para reservar"""
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    is_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    appointment = db.relationship('Appointment', backref='slot', uselist=False)
```

### 5. **Modelo: Appointment (Cita Reservada)**
Las citas reservadas por los miembros.

```python
class Appointment(db.Model):
    """Citas reservadas por los miembros"""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisor.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('appointment_slot.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Solicitante principal
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    
    # Participantes (para citas grupales)
    is_group = db.Column(db.Boolean, default=False)
    participants = db.relationship('AppointmentParticipant', backref='appointment', lazy=True)
    
    # Estado y confirmación
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    advisor_confirmed = db.Column(db.Boolean, default=False)
    advisor_confirmed_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)
    
    # Precio y pago
    base_price = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, default=0.0)
    discount_applied = db.Column(db.Float, default=0.0)
    membership_type = db.Column(db.String(50))  # Tipo de membresía al momento de reservar
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded
    
    # Notas
    user_notes = db.Column(db.Text)  # Notas del usuario al reservar
    advisor_notes = db.Column(db.Text)  # Notas del asesor
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref='appointments')
```

### 6. **Modelo: AppointmentParticipant (Participantes)**
Para citas grupales.

```python
class AppointmentParticipant(db.Model):
    """Participantes adicionales en citas grupales"""
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='appointment_participations')
```

### 7. **Modelo: AppointmentPricing (Reglas de Precio)**
Precios según membresía.

```python
class AppointmentPricing(db.Model):
    """Reglas de precio según tipo de membresía"""
    id = db.Column(db.Integer, primary_key=True)
    appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    membership_type = db.Column(db.String(50), nullable=False)  # basic, pro, premium
    price = db.Column(db.Float, default=0.0)  # 0 = incluido en membresía
    discount_percentage = db.Column(db.Float, default=0.0)
    is_included = db.Column(db.Boolean, default=False)  # Si está incluido en la membresía
    is_active = db.Column(db.Boolean, default=True)
```

---

## 🔄 Flujo de Trabajo

### **1. Configuración Administrativa**
1. Admin crea **AppointmentType** (ej: "Asesoría en Revisión de Artículos")
   - Define duración, precio base, si permite grupos
2. Admin asigna **Advisors** al tipo de cita
3. **Advisor** configura su **AdvisorAvailability**
   - Ej: Lunes 8am-12pm, Miércoles 2pm-6pm
4. Sistema genera **AppointmentSlots** de forma híbrida
   - Automáticamente: a partir de la disponibilidad semanal hasta un horizonte configurable
   - Manualmente: el asesor puede crear/editar slots especiales o cerrar espacios puntuales

### **2. Reserva por Miembro**
1. Miembro ve servicios disponibles en dashboard
2. Click en "Hacer Cita" → Ve tipos de citas disponibles
3. Selecciona tipo de cita → Ve asesores disponibles
4. Selecciona asesor → Ve slots disponibles
5. Selecciona slot → Si es grupal, invita participantes
6. Sistema calcula precio según membresía
7. Si requiere pago → Proceso de pago
8. Cita queda en estado "pending"
9. Notificación por email a asesor y miembro

### **3. Confirmación por Asesor**
1. Asesor recibe notificación
2. Asesor ve cita en panel administrativo
3. Asesor confirma o rechaza
4. Si confirma:
   - Estado → "confirmed"
   - Notificación a miembro
   - Si es virtual, se genera link de reunión
5. Si rechaza:
   - Estado → "cancelled"
   - Slot vuelve a estar disponible
   - Notificación a miembro con razón

### **4. Gestión de Prioridad**
- Los miembros con mejor membresía ven slots primero
- Si hay conflicto, prioridad: Premium > Pro > Basic
- Sistema puede reservar slots automáticamente para premium

---

## 💰 Sistema de Precios

### **Reglas de Precio por Membresía:**

| Membresía | Precio Base | Descuento | Precio Final | Incluido |
|-----------|-------------|-----------|--------------|----------|
| Basic     | $50.00      | 0%        | $50.00       | No       |
| Pro       | $50.00      | 20%       | $40.00       | No       |
| Premium   | $50.00      | 100%      | $0.00        | Sí       |

**Implementación:**
- Si `is_included = True` → Precio = $0.00
- Si `discount_percentage > 0` → Aplicar descuento
- Si `price` está definido → Usar precio específico para esa membresía

---

## 📧 Notificaciones

### **Email al Reservar:**
- Miembro: Confirmación de reserva pendiente
- Asesor: Nueva solicitud de cita

### **Email al Confirmar:**
- Miembro: Cita confirmada + Link de reunión (si virtual)
- Asesor: Recordatorio de cita

### **Email al Cancelar:**
- Miembro: Cita cancelada + Razón
- Asesor: Notificación de cancelación

---

## 🎨 Interfaz de Usuario

### **Dashboard de Miembro:**
- Icono "Hacer Cita" en servicios
- Lista de citas próximas
- Historial de citas

### **Panel de Asesor:**
- Calendario de citas
- Solicitudes pendientes
- Disponibilidad semanal
- Historial de citas dadas

### **Panel Administrativo:**
- Gestión de tipos de citas
- Gestión de asesores
- Configuración de precios
- Reportes de citas

---

## 🔗 Relación con Servicios/Beneficios

- Los **AppointmentType** pueden estar relacionados con **Benefit**
- Los miembros ven qué servicios tienen disponibles según su membresía
- Los servicios pueden tener múltiples formas:
  - Incluidos en membresía (gratis)
  - Con descuento según membresía
  - Con costo fijo

---

## ❓ Preguntas Pendientes para Confirmar

1. **¿Los asesores son usuarios del sistema o externos?**
   - Si son usuarios → Relación con User
   - Si son externos → Modelo separado

2. **¿Cómo se generan los slots?**
   - ¿Automático cada semana?
   - ¿Manual por asesor?
   - ¿Hasta cuántos días en el futuro?

3. **¿Las citas grupales tienen límite de participantes?**
   - ✅ Sí, configurable por tipo de cita. El solicitante principal gestiona invitados (de preferencia miembros).

4. **¿Qué pasa si un asesor cancela?**
   - ✅ Debe enviar correo a todos los participantes. No se contempla reasignación automática, pero el sistema debe facilitar reagendamiento.

5. **¿Integración con calendario externo?**
   - ✅ Sí (Google/Outlook) para disponibilidad y recordatorios.

6. **¿Recordatorios automáticos?**
   - ✅ Sí, siguiendo la lógica de Odoo (ej. 24 h y 1 h antes, configurables).

---

## 📝 Próximos Pasos

1. ✅ **Confirmar este análisis con el equipo**
2. ⏳ **Definir respuestas a preguntas pendientes**
3. ⏳ **Crear diagrama de base de datos**
4. ⏳ **Definir endpoints de API**
5. ⏳ **Diseñar mockups de interfaz**
6. ⏳ **Implementar modelos**
7. ⏳ **Implementar lógica de negocio**
8. ⏳ **Crear interfaces de usuario**

---

## ✅ Respuestas Confirmadas

1. **Asesores**: son usuarios locales del sistema; se les asigna explícitamente el rol de asesor.
2. **Generación de slots**: combinación manual + automática. El sistema genera slots recurrentes, pero los asesores pueden ajustarlos.
3. **Cupos en citas grupales**: configurables por tipo de servicio.
4. **Cancelación por asesor**: caso excepcional; debe disparar correos a todos los participantes y dejar registro para reagendar.
5. **Integraciones externas**: requerido soporte para calendarios (Google/Outlook) y enlaces de videollamada.
6. **Recordatorios automáticos**: obligatorios, enviando correos/alertas similares a Odoo (24 h / 1 h antes por defecto).

---

**Fecha de Análisis:** 2025-11-26  
**Versión:** 1.1  
**Estado:** 🟡 En planificación (preguntas críticas resueltas)

