# FUNCIONAMIENTO COMPLETO: Sistema de Citas con Pago/Abono para Servicios

## 📋 ÍNDICE
1. [Modificaciones al Modelo Service](#1-modificaciones-al-modelo-service)
2. [Flujo Completo del Sistema](#2-flujo-completo-del-sistema)
3. [Rutas y Endpoints](#3-rutas-y-endpoints)
4. [Funciones Auxiliares](#4-funciones-auxiliares)
5. [Templates Necesarios](#5-templates-necesarios)
6. [Migración de Base de Datos](#6-migración-de-base-de-datos)
7. [Validaciones y Reglas de Negocio](#7-validaciones-y-reglas-de-negocio)

---

## 1. MODIFICACIONES AL MODELO SERVICE

### 1.1 Campos a Agregar

```python
# En app.py, modelo Service (después de línea 2042)

# Campos para sistema de citas con pago
appointment_type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=True)
requires_payment_before_appointment = db.Column(db.Boolean, default=True)
deposit_amount = db.Column(db.Float, nullable=True)  # Abono fijo (ej: $50)
deposit_percentage = db.Column(db.Float, nullable=True)  # Abono porcentual (ej: 0.5 = 50%)
```

### 1.2 Método Helper para Calcular Abono

```python
# Agregar al modelo Service (después del método pricing_for_membership)

def calculate_deposit(self, user_membership_type=None):
    """
    Calcula el monto de abono requerido para este servicio.
    
    Retorna:
        dict con:
        - deposit_amount: monto a pagar como abono
        - final_price: precio total del servicio
        - remaining_balance: saldo pendiente después del abono
        - requires_full_payment: si requiere pago completo
    """
    pricing = self.pricing_for_membership(user_membership_type)
    final_price = pricing['final_price']
    
    # Si el servicio es gratuito, no requiere abono
    if final_price <= 0:
        return {
            'deposit_amount': 0.0,
            'final_price': 0.0,
            'remaining_balance': 0.0,
            'requires_full_payment': False
        }
    
    # Calcular abono
    deposit_amount = final_price  # Por defecto, pago completo
    
    if self.deposit_amount:
        # Abono fijo
        deposit_amount = min(self.deposit_amount, final_price)
    elif self.deposit_percentage:
        # Abono porcentual
        deposit_amount = final_price * self.deposit_percentage
    
    remaining_balance = max(0.0, final_price - deposit_amount)
    
    return {
        'deposit_amount': deposit_amount,
        'final_price': final_price,
        'remaining_balance': remaining_balance,
        'requires_full_payment': (remaining_balance == 0.0)
    }

def requires_appointment(self):
    """Verifica si el servicio requiere cita."""
    return self.appointment_type_id is not None and self.is_active

def is_free_service(self, user_membership_type=None):
    """Verifica si el servicio es gratuito para el usuario."""
    pricing = self.pricing_for_membership(user_membership_type)
    return pricing['final_price'] <= 0 or pricing['is_included']
```

---

## 2. FLUJO COMPLETO DEL SISTEMA

### 2.1 Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Usuario ve lista de servicios                    │
│  ─────────────────────────────────────────────────────────  │
│  • Servicios gratuitos: Botón "Acceder"                    │
│  • Servicios de pago: Botón "Solicitar Cita"               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: GET /services/<id>/request-appointment            │
│  ─────────────────────────────────────────────────────────  │
│  Validaciones:                                              │
│  ✓ Servicio existe y está activo                          │
│  ✓ Servicio tiene appointment_type_id                      │
│  ✓ Usuario tiene membresía activa                         │
│                                                             │
│  Mostrar:                                                   │
│  • Datos del miembro (solo lectura)                        │
│  • Campo: Descripción del caso (50-1000 chars)           │
│  • Lista de slots disponibles                              │
│  • Resumen de precios:                                     │
│    - Precio total: $XXX                                    │
│    - Abono requerido: $YYY                                 │
│    - Saldo pendiente: $ZZZ                                 │
│  • Métodos de pago disponibles                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: POST /services/<id>/request-appointment          │
│  ─────────────────────────────────────────────────────────  │
│  Validaciones:                                              │
│  ✓ Descripción del caso (50-1000 chars)                   │
│  ✓ Slot seleccionado existe y está disponible              │
│  ✓ Método de pago válido                                   │
│                                                             │
│  Acciones:                                                  │
│  1. Crear Payment (status: pending)                        │
│  2. Guardar metadata (service_id, slot_id, descripción)   │
│  3. Procesar pago según método                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 4: Procesamiento de Pago                            │
│  ─────────────────────────────────────────────────────────  │
│  • Stripe: Redirigir a checkout                            │
│  • Banco General/Yappy: Generar URL de pago               │
│  • Efectivo: Marcar como awaiting_confirmation             │
│                                                             │
│  Si pago exitoso:                                           │
│  → Crear Appointment                                        │
│  → Reservar Slot                                            │
│  → Vincular Payment                                         │
│  → Notificar al asesor                                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 5: Webhook/Callback de Pago Exitoso                  │
│  ─────────────────────────────────────────────────────────  │
│  • Actualizar Payment (status: succeeded)                 │
│  • Crear Appointment desde metadata                        │
│  • Redirigir a confirmación                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 6: Confirmación                                       │
│  ─────────────────────────────────────────────────────────  │
│  • Mostrar resumen de cita agendada                        │
│  • Detalles de pago                                         │
│  • Si hay saldo pendiente, opción de pagar                  │
│  • Link a "Ver mis citas"                                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Estados de la Cita

**Appointment.status:**
- `pending`: Creada, esperando confirmación del asesor
- `confirmed`: Confirmada por el asesor
- `cancelled`: Cancelada
- `completed`: Completada
- `no_show`: No asistió

**Appointment.payment_status:**
- `pending`: Sin pago
- `partial`: Abono pagado (falta saldo)
- `paid`: Pago completo
- `refunded`: Reembolsado

---

## 3. RUTAS Y ENDPOINTS

**Nota:** Las rutas de pago para citas (Stripe, estado de pago, callback `/api/payments/<id>/success`, historial, webhook) están en el blueprint **`payments_checkout`**: `backend/nodeone/modules/payments_checkout/routes.py`. Los fragmentos de abajo describen el comportamiento; los decoradores reales usan `@payments_checkout_bp.route(...)`.

### 3.1 Ruta: Mostrar Formulario de Solicitud

**Archivo:** `backend/app.py` o módulo de servicios (según despliegue; agregar después de la ruta `/services`)

```python
@app.route('/services/<int:service_id>/request-appointment')
@login_required
def service_request_appointment(service_id):
    """
    Muestra el formulario para solicitar una cita de un servicio.
    """
    from app import Service, AppointmentType, AppointmentSlot, ServicePricingRule
    from datetime import datetime
    import json
    
    # Validar servicio
    service = Service.query.get_or_404(service_id)
    if not service.is_active:
        flash('Este servicio no está disponible.', 'error')
        return redirect(url_for('services'))
    
    # Verificar que el servicio requiere cita
    if not service.requires_appointment():
        flash('Este servicio no requiere cita.', 'info')
        return redirect(url_for('services'))
    
    # Verificar membresía activa
    membership = current_user.get_active_membership()
    if not membership:
        flash('Necesitas una membresía activa para solicitar citas.', 'warning')
        return redirect(url_for('services'))
    
    membership_type = membership.membership_type
    
    # Verificar si el servicio es gratuito
    if service.is_free_service(membership_type):
        flash('Este servicio es gratuito y no requiere cita con pago.', 'info')
        return redirect(url_for('services'))
    
    # Obtener tipo de cita asociado
    appointment_type = AppointmentType.query.get(service.appointment_type_id)
    if not appointment_type or not appointment_type.is_active:
        flash('El tipo de cita asociado no está disponible.', 'error')
        return redirect(url_for('services'))
    
    # Calcular precios y abono
    pricing = service.pricing_for_membership(membership_type)
    deposit_info = service.calculate_deposit(membership_type)
    
    # Obtener asesores asignados
    advisors = [
        assignment.advisor for assignment in appointment_type.advisor_assignments
        if assignment.is_active and assignment.advisor.is_active
    ]
    
    # Obtener slots disponibles (próximos 30 días)
    available_slots = AppointmentSlot.query.filter(
        AppointmentSlot.appointment_type_id == service.appointment_type_id,
        AppointmentSlot.start_datetime >= datetime.utcnow(),
        AppointmentSlot.start_datetime <= datetime.utcnow() + timedelta(days=30),
        AppointmentSlot.is_available == True
    ).order_by(AppointmentSlot.start_datetime.asc()).limit(50).all()
    
    # Obtener métodos de pago disponibles
    payment_methods = {}
    if stripe:
        payment_methods['stripe'] = 'Tarjeta de Crédito/Débito (Stripe)'
    payment_methods['banco_general'] = 'Banco General'
    payment_methods['yappy'] = 'Yappy'
    payment_methods['cash'] = 'Efectivo (Requiere verificación)'
    
    return render_template('services/request_appointment.html',
                         service=service,
                         appointment_type=appointment_type,
                         advisors=advisors,
                         membership=membership,
                         pricing=pricing,
                         deposit_info=deposit_info,
                         available_slots=available_slots,
                         payment_methods=payment_methods,
                         user=current_user)
```

### 3.2 Ruta: Procesar Solicitud y Pago

```python
@app.route('/services/<int:service_id>/request-appointment', methods=['POST'])
@login_required
def service_request_appointment_submit(service_id):
    """
    Procesa la solicitud de cita y crea el pago.
    """
    from app import Service, AppointmentSlot, Payment, db
    from datetime import datetime
    import json
    import secrets
    
    # Validar servicio
    service = Service.query.get_or_404(service_id)
    if not service.is_active or not service.requires_appointment():
        flash('Este servicio no está disponible para citas.', 'error')
        return redirect(url_for('services'))
    
    # Verificar membresía
    membership = current_user.get_active_membership()
    if not membership:
        flash('Necesitas una membresía activa.', 'warning')
        return redirect(url_for('services'))
    
    # Validar datos del formulario
    slot_id = request.form.get('slot_id', type=int)
    case_description = request.form.get('case_description', '').strip()
    payment_method = request.form.get('payment_method', '').strip()
    
    # Validar descripción del caso
    if not case_description or len(case_description) < 50:
        flash('La descripción del caso debe tener al menos 50 caracteres.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    if len(case_description) > 1000:
        flash('La descripción del caso no puede exceder 1000 caracteres.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Validar slot
    if not slot_id:
        flash('Debes seleccionar un horario disponible.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    slot = AppointmentSlot.query.get_or_404(slot_id)
    
    # Verificar que el slot pertenece al tipo de cita del servicio
    if slot.appointment_type_id != service.appointment_type_id:
        flash('El horario seleccionado no corresponde a este servicio.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Verificar disponibilidad del slot
    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('Este horario ya no está disponible. Por favor selecciona otro.', 'warning')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Validar método de pago
    valid_methods = ['stripe', 'banco_general', 'yappy', 'cash']
    if payment_method not in valid_methods:
        flash('Método de pago inválido.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
    
    # Calcular precios y abono
    membership_type = membership.membership_type
    pricing = service.pricing_for_membership(membership_type)
    deposit_info = service.calculate_deposit(membership_type)
    
    deposit_amount = deposit_info['deposit_amount']
    final_price = deposit_info['final_price']
    
    # Crear Payment con metadata
    payment_metadata = {
        'service_id': service.id,
        'service_name': service.name,
        'slot_id': slot.id,
        'slot_datetime': slot.start_datetime.isoformat(),
        'case_description': case_description,
        'final_price': final_price,
        'deposit_amount': deposit_amount,
        'remaining_balance': deposit_info['remaining_balance'],
        'appointment_type_id': service.appointment_type_id,
        'advisor_id': slot.advisor_id
    }
    
    payment = Payment(
        user_id=current_user.id,
        payment_method=payment_method,
        amount=int(deposit_amount * 100),  # Convertir a centavos
        currency='usd',
        status='pending',
        membership_type='service_appointment',
        payment_metadata=json.dumps(payment_metadata)
    )
    
    db.session.add(payment)
    db.session.flush()  # Para obtener el ID del payment
    
    # Procesar pago según método
    try:
        if payment_method == 'stripe':
            # Redirigir a Stripe Checkout
            return redirect_to_stripe_checkout(payment, service, slot)
        
        elif payment_method in ['banco_general', 'yappy']:
            # Generar URL de pago externo
            payment_url = generate_external_payment_url(payment, payment_method)
            payment.payment_url = payment_url
            db.session.commit()
            
            flash(f'Redirigiendo a {payment_method.upper()} para completar el pago...', 'info')
            return redirect(payment_url)
        
        elif payment_method == 'cash':
            # Marcar como awaiting_confirmation (requiere verificación manual)
            payment.status = 'awaiting_confirmation'
            payment.payment_metadata = json.dumps({
                **payment_metadata,
                'requires_manual_verification': True
            })
            db.session.commit()
            
            flash('Tu solicitud ha sido registrada. Un administrador verificará el pago en efectivo y confirmará tu cita.', 'info')
            return redirect(url_for('payments_checkout.payment_status', payment_id=payment.id))
        
        else:
            raise ValueError(f'Método de pago no soportado: {payment_method}')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar el pago: {str(e)}', 'error')
        return redirect(url_for('service_request_appointment', service_id=service_id))
```

### 3.3 Ruta: Callback de Pago Exitoso

```python
@payments_checkout_bp.route('/api/payments/<int:payment_id>/success')
@login_required
def service_payment_success_callback(payment_id):
    """
    Callback cuando un pago es exitoso. Crea el appointment.
    """
    from app import Payment, Service, AppointmentSlot, Appointment, db, ActivityLog
    import json
    
    payment = Payment.query.get_or_404(payment_id)
    
    # Verificar que el pago pertenece al usuario
    if payment.user_id != current_user.id:
        flash('No tienes permiso para acceder a este pago.', 'error')
        return redirect(url_for('services'))
    
    # Verificar que el pago fue exitoso
    if payment.status not in ['succeeded', 'awaiting_confirmation']:
        flash('El pago no se ha completado aún.', 'warning')
        return redirect(url_for('payments_checkout.payment_status', payment_id=payment_id))
    
    # Verificar que no se haya creado ya el appointment
    existing_appointment = Appointment.query.filter_by(payment_id=payment_id).first()
    if existing_appointment:
        flash('La cita ya fue creada anteriormente.', 'info')
        return redirect(url_for('appointments.appointments_home'))
    
    # Extraer metadata
    try:
        metadata = json.loads(payment.payment_metadata)
    except:
        flash('Error al procesar los datos del pago.', 'error')
        return redirect(url_for('services'))
    
    service_id = metadata.get('service_id')
    slot_id = metadata.get('slot_id')
    case_description = metadata.get('case_description')
    final_price = metadata.get('final_price', 0.0)
    deposit_amount = metadata.get('deposit_amount', 0.0)
    
    # Validar que el servicio y slot aún existen
    service = Service.query.get(service_id)
    slot = AppointmentSlot.query.get(slot_id)
    
    if not service or not slot:
        flash('Error: El servicio o horario seleccionado ya no está disponible.', 'error')
        return redirect(url_for('services'))
    
    # Verificar disponibilidad del slot
    if not slot.is_available or slot.remaining_seats() <= 0:
        flash('El horario seleccionado ya no está disponible. Contacta a soporte.', 'error')
        return redirect(url_for('services'))
    
    # Determinar estado de pago
    if deposit_amount >= final_price:
        payment_status = 'paid'
    else:
        payment_status = 'partial'
    
    # Obtener membresía
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None
    
    # Calcular precios finales
    pricing = service.pricing_for_membership(membership_type)
    
    # Crear Appointment
    appointment = Appointment(
        appointment_type_id=service.appointment_type_id,
        advisor_id=slot.advisor_id,
        slot_id=slot.id,
        service_id=service.id,
        payment_id=payment.id,
        user_id=current_user.id,
        membership_type=membership_type,
        start_datetime=slot.start_datetime,
        end_datetime=slot.end_datetime,
        status='pending',  # Esperando confirmación del asesor
        base_price=pricing['base_price'],
        final_price=final_price,
        discount_applied=pricing['base_price'] - pricing['final_price'],
        payment_status=payment_status,
        payment_method=payment.payment_method,
        user_notes=case_description
    )
    
    # Reservar slot
    slot.reserved_seats = (slot.reserved_seats or 0) + 1
    if slot.remaining_seats() == 0:
        slot.is_available = False
    
    db.session.add(appointment)
    db.session.commit()
    
    # Log actividad
    ActivityLog.log_activity(
        current_user.id,
        'service_appointment_created',
        'appointment',
        appointment.id,
        f'Cita creada para servicio {service.name} - Referencia: {appointment.reference}',
        request
    )
    
    # TODO: Enviar email de confirmación al usuario
    # TODO: Enviar notificación al asesor
    
    flash(f'¡Cita agendada exitosamente! Referencia: {appointment.reference}', 'success')
    return redirect(url_for('appointments.appointments_home'))
```

### 3.4 Ruta: Ver Estado de Pago

```python
@payments_checkout_bp.route('/payments/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """
    Muestra el estado de un pago y permite completar el proceso.
    """
    from app import Payment, Service, Appointment, db
    import json
    
    payment = Payment.query.get_or_404(payment_id)
    
    # Verificar que el pago pertenece al usuario
    if payment.user_id != current_user.id:
        flash('No tienes permiso para acceder a este pago.', 'error')
        return redirect(url_for('services'))
    
    # Extraer metadata
    metadata = {}
    if payment.payment_metadata:
        try:
            metadata = json.loads(payment.payment_metadata)
        except:
            pass
    
    # Verificar si ya se creó el appointment
    appointment = Appointment.query.filter_by(payment_id=payment_id).first()
    
    # Si el pago fue exitoso y no hay appointment, redirigir a crear
    if payment.status == 'succeeded' and not appointment:
        return redirect(url_for('payments_checkout.service_payment_success_callback', payment_id=payment_id))
    
    service = None
    if metadata.get('service_id'):
        service = Service.query.get(metadata.get('service_id'))
    
    return render_template('payments/payment_status.html',
                         payment=payment,
                         appointment=appointment,
                         service=service,
                         metadata=metadata)
```

---

## 4. FUNCIONES AUXILIARES

### 4.1 Redirigir a Stripe Checkout

```python
def redirect_to_stripe_checkout(payment, service, slot):
    """
    Crea una sesión de Stripe Checkout y redirige al usuario.
    """
    from app import db
    import stripe
    
    if not stripe:
        flash('El método de pago con tarjeta no está disponible.', 'error')
        return redirect(url_for('service_request_appointment', service_id=service.id))
    
    try:
        # Crear sesión de checkout
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Cita: {service.name}',
                        'description': f'Abono para cita el {slot.start_datetime.strftime("%d/%m/%Y %H:%M")}'
                    },
                    'unit_amount': int(payment.amount),  # Ya está en centavos
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payments_checkout.service_payment_success_callback', payment_id=payment.id, _external=True),
            cancel_url=url_for('service_request_appointment', service_id=service.id, _external=True),
            metadata={
                'payment_id': payment.id,
                'service_id': service.id,
                'slot_id': slot.id
            }
        )
        
        # Guardar referencia de Stripe
        payment.payment_reference = checkout_session.id
        payment.payment_url = checkout_session.url
        db.session.commit()
        
        return redirect(checkout_session.url)
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear la sesión de pago: {str(e)}', 'error')
        return redirect(url_for('service_request_appointment', service_id=service.id))
```

### 4.2 Generar URL de Pago Externo

```python
def generate_external_payment_url(payment, payment_method):
    """
    Genera URL para pagos externos (Banco General, Yappy).
    """
    from app import db
    
    # URL base del sistema
    base_url = request.url_root.rstrip('/')
    
    # URL de callback
    callback_url = url_for('payments_checkout.service_payment_success_callback', payment_id=payment.id, _external=True)
    cancel_url = url_for('services', _external=True)
    
    # Generar URL según el método
    if payment_method == 'banco_general':
        # TODO: Integrar con API de Banco General
        # Por ahora, retornar URL de confirmación manual
        return url_for('payments_checkout.payment_status', payment_id=payment.id, _external=True)
    
    elif payment_method == 'yappy':
        # TODO: Integrar con API de Yappy
        # Por ahora, retornar URL de confirmación manual
        return url_for('payments_checkout.payment_status', payment_id=payment.id, _external=True)
    
    return callback_url
```

### 4.3 Webhook de Stripe

**Ruta real:** `POST /stripe-webhook` (blueprint `payments_checkout`, sin prefijo).

```python
@payments_checkout_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """
    Webhook de Stripe para actualizar el estado del pago.
    """
    from app import Payment, db
    import stripe
    import json
    
    if not stripe:
        return jsonify({'error': 'Stripe no está configurado'}), 400
    
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Manejar eventos
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment_id = session.get('metadata', {}).get('payment_id')
        
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                payment.status = 'succeeded'
                payment.paid_at = datetime.utcnow()
                db.session.commit()
    
    return jsonify({'status': 'success'}), 200
```

---

## 5. TEMPLATES NECESARIOS

### 5.1 Template: Formulario de Solicitud (`templates/services/request_appointment.html`)

```html
{% extends "base.html" %}

{% block title %}Solicitar Cita - {{ service.name }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-lg-8 mx-auto">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">
                        <i class="fas fa-calendar-check me-2"></i>
                        Solicitar Cita: {{ service.name }}
                    </h4>
                </div>
                <div class="card-body">
                    <form method="POST" action="{{ url_for('service_request_appointment_submit', service_id=service.id) }}">
                        
                        <!-- Datos del Miembro (Solo Lectura) -->
                        <div class="mb-4">
                            <h5 class="text-muted">Datos del Miembro</h5>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Nombre Completo</label>
                                    <input type="text" class="form-control" value="{{ user.first_name }} {{ user.last_name }}" readonly>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Email</label>
                                    <input type="email" class="form-control" value="{{ user.email }}" readonly>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Teléfono</label>
                                    <input type="text" class="form-control" value="{{ user.phone or 'No registrado' }}" readonly>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Tipo de Membresía</label>
                                    <input type="text" class="form-control" value="{{ membership.membership_type|upper }}" readonly>
                                </div>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <!-- Descripción del Caso -->
                        <div class="mb-4">
                            <label for="case_description" class="form-label">
                                Describe brevemente tu caso o necesidad <span class="text-danger">*</span>
                            </label>
                            <textarea 
                                class="form-control" 
                                id="case_description" 
                                name="case_description" 
                                rows="5" 
                                minlength="50" 
                                maxlength="1000" 
                                placeholder="Describe brevemente tu caso o necesidad (mínimo 50 caracteres)..."
                                required></textarea>
                            <div class="form-text">
                                <span id="char_count">0</span> / 1000 caracteres (mínimo 50)
                            </div>
                        </div>
                        
                        <hr>
                        
                        <!-- Seleccionar Horario -->
                        <div class="mb-4">
                            <label class="form-label">
                                Selecciona un horario disponible <span class="text-danger">*</span>
                            </label>
                            {% if available_slots %}
                                <div class="list-group">
                                    {% for slot in available_slots %}
                                        <label class="list-group-item">
                                            <input 
                                                type="radio" 
                                                name="slot_id" 
                                                value="{{ slot.id }}" 
                                                class="form-check-input me-2" 
                                                required>
                                            <div class="d-flex justify-content-between align-items-center">
                                                <div>
                                                    <strong>{{ slot.start_datetime.strftime('%A, %d de %B de %Y') }}</strong><br>
                                                    <small class="text-muted">
                                                        {{ slot.start_datetime.strftime('%I:%M %p') }} - {{ slot.end_datetime.strftime('%I:%M %p') }}
                                                        ({{ appointment_type.duration_minutes }} minutos)
                                                    </small><br>
                                                    {% if slot.advisor %}
                                                        <small>Asesor: {{ slot.advisor.user.first_name }} {{ slot.advisor.user.last_name }}</small>
                                                    {% endif %}
                                                </div>
                                                <div class="text-end">
                                                    {% if slot.capacity > 1 %}
                                                        <span class="badge bg-info">{{ slot.remaining_seats() }} disponibles</span>
                                                    {% endif %}
                                                </div>
                                            </div>
                                        </label>
                                    {% endfor %}
                                </div>
                            {% else %}
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle me-2"></i>
                                    No hay horarios disponibles en este momento. 
                                    <a href="{{ url_for('appointments.appointments_home') }}">Ver otras opciones</a>
                                </div>
                            {% endif %}
                        </div>
                        
                        <hr>
                        
                        <!-- Resumen de Precios -->
                        <div class="mb-4">
                            <h5 class="text-muted">Resumen de Precios</h5>
                            <table class="table table-bordered">
                                <tr>
                                    <td>Precio Total del Servicio:</td>
                                    <td class="text-end"><strong>${{ "%.2f"|format(deposit_info.final_price) }}</strong></td>
                                </tr>
                                <tr>
                                    <td>Abono Requerido:</td>
                                    <td class="text-end"><strong class="text-primary">${{ "%.2f"|format(deposit_info.deposit_amount) }}</strong></td>
                                </tr>
                                {% if deposit_info.remaining_balance > 0 %}
                                <tr>
                                    <td>Saldo Pendiente:</td>
                                    <td class="text-end"><strong class="text-warning">${{ "%.2f"|format(deposit_info.remaining_balance) }}</strong></td>
                                </tr>
                                {% endif %}
                            </table>
                        </div>
                        
                        <!-- Método de Pago -->
                        <div class="mb-4">
                            <label class="form-label">
                                Método de Pago <span class="text-danger">*</span>
                            </label>
                            <div class="list-group">
                                {% for method_key, method_name in payment_methods.items() %}
                                <label class="list-group-item">
                                    <input 
                                        type="radio" 
                                        name="payment_method" 
                                        value="{{ method_key }}" 
                                        class="form-check-input me-2" 
                                        required>
                                    {{ method_name }}
                                </label>
                                {% endfor %}
                            </div>
                        </div>
                        
                        <!-- Botones -->
                        <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                            <a href="{{ url_for('services') }}" class="btn btn-secondary">
                                <i class="fas fa-times me-2"></i>Cancelar
                            </a>
                            <button type="submit" class="btn btn-primary" {% if not available_slots %}disabled{% endif %}>
                                <i class="fas fa-credit-card me-2"></i>Pagar y Agendar Cita
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Contador de caracteres
document.getElementById('case_description').addEventListener('input', function() {
    const count = this.value.length;
    document.getElementById('char_count').textContent = count;
    
    if (count < 50) {
        document.getElementById('char_count').classList.add('text-danger');
    } else {
        document.getElementById('char_count').classList.remove('text-danger');
    }
});
</script>
{% endblock %}
```

### 5.2 Template: Estado de Pago (`templates/payments/payment_status.html`)

```html
{% extends "base.html" %}

{% block title %}Estado de Pago{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-lg-8 mx-auto">
            <div class="card">
                <div class="card-header">
                    <h4 class="mb-0">Estado del Pago</h4>
                </div>
                <div class="card-body">
                    <!-- Estado del Pago -->
                    <div class="alert alert-{{ 'success' if payment.status == 'succeeded' else 'warning' if payment.status == 'pending' else 'info' }}">
                        <h5>
                            {% if payment.status == 'succeeded' %}
                                <i class="fas fa-check-circle me-2"></i>Pago Completado
                            {% elif payment.status == 'pending' %}
                                <i class="fas fa-clock me-2"></i>Pago Pendiente
                            {% elif payment.status == 'awaiting_confirmation' %}
                                <i class="fas fa-hourglass-half me-2"></i>Esperando Confirmación
                            {% else %}
                                <i class="fas fa-info-circle me-2"></i>Estado: {{ payment.status }}
                            {% endif %}
                        </h5>
                    </div>
                    
                    <!-- Detalles del Pago -->
                    <table class="table">
                        <tr>
                            <td><strong>Monto:</strong></td>
                            <td>${{ "%.2f"|format(payment.amount / 100) }}</td>
                        </tr>
                        <tr>
                            <td><strong>Método:</strong></td>
                            <td>{{ payment.payment_method|upper }}</td>
                        </tr>
                        <tr>
                            <td><strong>Referencia:</strong></td>
                            <td>{{ payment.payment_reference or 'N/A' }}</td>
                        </tr>
                    </table>
                    
                    <!-- Si hay appointment creado -->
                    {% if appointment %}
                        <div class="alert alert-success">
                            <h5><i class="fas fa-calendar-check me-2"></i>Cita Agendada</h5>
                            <p>Referencia: <strong>{{ appointment.reference }}</strong></p>
                            <p>Fecha: {{ appointment.start_datetime.strftime('%d/%m/%Y %I:%M %p') }}</p>
                            <a href="{{ url_for('appointments.appointments_home') }}" class="btn btn-primary">
                                Ver Mis Citas
                            </a>
                        </div>
                    {% elif payment.status == 'succeeded' %}
                        <!-- Si el pago fue exitoso pero no hay appointment, crear -->
                        <div class="alert alert-info">
                            <p>Procesando tu cita...</p>
                            <a href="{{ url_for('payments_checkout.service_payment_success_callback', payment_id=payment.id) }}" class="btn btn-primary">
                                Completar Proceso
                            </a>
                        </div>
                    {% endif %}
                    
                    <!-- Si hay URL de pago externo -->
                    {% if payment.payment_url and payment.status == 'pending' %}
                        <div class="d-grid">
                            <a href="{{ payment.payment_url }}" class="btn btn-primary" target="_blank">
                                Completar Pago
                            </a>
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 6. MIGRACIÓN DE BASE DE DATOS

### 6.1 Script de Migración

**Archivo:** `backend/migrate_service_appointment_fields.py`

```python
#!/usr/bin/env python3
"""
Migración: Agregar campos de citas y abono al modelo Service.
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def migrate():
    """Agregar campos nuevos a la tabla service."""
    
    with app.app_context():
        try:
            # Verificar si las columnas ya existen
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('service')]
            
            columns_to_add = []
            
            if 'appointment_type_id' not in existing_columns:
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN appointment_type_id INTEGER 
                    REFERENCES appointment_type(id)
                """)
            
            if 'requires_payment_before_appointment' not in existing_columns:
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN requires_payment_before_appointment BOOLEAN DEFAULT TRUE
                """)
            
            if 'deposit_amount' not in existing_columns:
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN deposit_amount FLOAT
                """)
            
            if 'deposit_percentage' not in existing_columns:
                columns_to_add.append("""
                    ALTER TABLE service 
                    ADD COLUMN deposit_percentage FLOAT
                """)
            
            if columns_to_add:
                print("Agregando columnas a la tabla service...")
                for sql in columns_to_add:
                    db.session.execute(text(sql))
                
                db.session.commit()
                print("✅ Migración completada exitosamente.")
            else:
                print("✅ Todas las columnas ya existen. No se requiere migración.")
            
            # Crear índices
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_service_appointment_type_id 
                    ON service(appointment_type_id)
                """))
                db.session.commit()
                print("✅ Índices creados.")
            except Exception as e:
                print(f"⚠️  Error al crear índices (puede que ya existan): {e}")
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en la migración: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("MIGRACIÓN: Campos de Citas y Abono en Service")
    print("=" * 60)
    
    if migrate():
        print("\n✅ Migración completada exitosamente.")
    else:
        print("\n❌ La migración falló. Revisa los errores arriba.")
        sys.exit(1)
```

### 6.2 Ejecutar Migración

```bash
cd /home/relaticpanama2025/projects/membresia-relatic
source venv/bin/activate
python backend/migrate_service_appointment_fields.py
```

---

## 7. VALIDACIONES Y REGLAS DE NEGOCIO

### 7.1 Validaciones en el Formulario

1. **Descripción del caso:**
   - Mínimo: 50 caracteres
   - Máximo: 1000 caracteres
   - Requerido

2. **Slot seleccionado:**
   - Debe existir
   - Debe pertenecer al `appointment_type_id` del servicio
   - Debe estar disponible (`is_available = True`)
   - Debe tener capacidad (`remaining_seats() > 0`)
   - Debe ser futuro (`start_datetime >= ahora`)

3. **Método de pago:**
   - Debe ser uno de los métodos disponibles
   - Debe estar habilitado en el sistema

4. **Membresía:**
   - Usuario debe tener membresía activa
   - El servicio debe estar disponible para su tipo de membresía

### 7.2 Reglas de Negocio

1. **Abono:**
   - Si `deposit_amount` está configurado → usar ese monto
   - Si `deposit_percentage` está configurado → calcular porcentaje
   - Si ambos son NULL → requiere pago completo
   - El abono nunca puede exceder el precio final

2. **Creación de Appointment:**
   - Solo se crea después de pago exitoso
   - Se vincula con `service_id` y `payment_id`
   - Estado inicial: `pending` (esperando confirmación del asesor)
   - `payment_status`: `paid` si abono = precio total, `partial` si hay saldo

3. **Reserva de Slot:**
   - Se reserva inmediatamente al crear el appointment
   - Si el slot se llena, se marca como `is_available = False`
   - Si se cancela la cita, se libera el slot

4. **Cancelación:**
   - Usuario puede cancelar si faltan más de 12 horas
   - Si hay abono pagado, aplicar política de reembolso
   - Liberar slot si se cancela

---

## 8. INTEGRACIÓN CON VISTA DE SERVICIOS

### 8.1 Modificar Template de Servicios

En `templates/services.html`, agregar botón "Solicitar Cita" para servicios que requieren cita:

```html
{% if service.requires_appointment() and not service.is_free_service(user_membership_type) %}
    <a href="{{ url_for('service_request_appointment', service_id=service.id) }}" 
       class="btn btn-primary btn-sm">
        <i class="fas fa-calendar-check me-2"></i>Solicitar Cita
    </a>
{% endif %}
```

---

## 9. RESUMEN DE ARCHIVOS A CREAR/MODIFICAR

### Archivos a Modificar:
1. `backend/app.py` (o modelos en módulos) - Campos al modelo Service y métodos helper
2. `backend/nodeone/modules/payments_checkout/routes.py` - Checkout, callbacks de pago, estado, webhook Stripe
3. `templates/services.html` - Agregar botón "Solicitar Cita"

### Archivos a Crear:
1. `templates/services/request_appointment.html` - Formulario de solicitud
2. `templates/payments/payment_status.html` - Estado de pago
3. `backend/migrate_service_appointment_fields.py` - Script de migración

### Funciones auxiliares (implementadas en `payments_checkout`):
1. `redirect_to_stripe_checkout()` — `nodeone/modules/payments_checkout/routes.py`
2. `generate_external_payment_url()` — mismo archivo
3. `stripe_webhook()` — mismo archivo (`/stripe-webhook`)

---

## 10. PRUEBAS SUGERIDAS

1. ✅ Servicio gratuito no muestra botón de cita
2. ✅ Servicio de pago muestra botón "Solicitar Cita"
3. ✅ Formulario valida descripción (50-1000 chars)
4. ✅ Formulario valida selección de slot
5. ✅ Cálculo correcto de abono (fijo, porcentual, completo)
6. ✅ Creación de Payment con metadata correcta
7. ✅ Creación de Appointment después de pago exitoso
8. ✅ Reserva correcta de slot
9. ✅ Vinculación correcta service_id y payment_id
10. ✅ Estados de pago correctos (paid/partial)

---

**FIN DEL DOCUMENTO**
