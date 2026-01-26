# 🧪 GUÍA DE PRUEBA: Sistema de Citas con Pago/Abono para Servicios

## ✅ Estado de la Implementación

**Todos los pasos completados:**
- ✅ Paso 1: Migración de base de datos
- ✅ Paso 2: Rutas y funciones auxiliares
- ✅ Paso 3: Templates HTML
- ✅ Paso 4: Botón en vista de servicios
- ✅ Paso 5: Configuración de servicio de prueba

---

## 📋 Servicio de Prueba Configurado

**Servicio:** Artículos/Revistas (ID: 1)
- **Precio base:** $50.00
- **Tipo de cita:** Asesoría técnica en configuración de MS O365
- **Abono configurado:** 50% del precio final
- **Slots disponibles:** 5 slots creados para los próximos días

---

## 🧪 Pasos para Probar el Sistema

### 1. Acceder a la Aplicación

1. Abre tu navegador y ve a la URL de la aplicación
2. Inicia sesión con un usuario que tenga membresía activa

### 2. Navegar a Servicios

1. Ve a la sección **"Servicios"** desde el menú
2. Busca el servicio **"Artículos/Revistas"**
3. **Verifica que aparezca el botón "Solicitar Cita"** (debe estar visible si el servicio tiene `appointment_type_id` configurado y no es gratuito)

### 3. Solicitar Cita

1. Haz clic en el botón **"Solicitar Cita"**
2. Deberías ver el formulario con:
   - ✅ Datos del miembro (pre-llenados, solo lectura)
   - ✅ Campo de descripción del caso
   - ✅ Lista de slots disponibles
   - ✅ Resumen de precios (total, abono, saldo pendiente)
   - ✅ Métodos de pago

### 4. Completar el Formulario

1. **Descripción del caso:**
   - Escribe al menos 50 caracteres
   - El contador debe mostrar el número de caracteres
   - Máximo 1000 caracteres

2. **Seleccionar horario:**
   - Selecciona uno de los slots disponibles
   - Verifica que muestre fecha, hora y asesor

3. **Revisar precios:**
   - Precio total: $50.00 (o con descuento según tu membresía)
   - Abono requerido: 50% del precio final
   - Saldo pendiente: 50% del precio final

4. **Seleccionar método de pago:**
   - Stripe (si está disponible)
   - Banco General
   - Yappy
   - Efectivo

### 5. Procesar el Pago

1. Haz clic en **"Pagar y Agendar Cita"**
2. Según el método seleccionado:
   - **Stripe:** Redirige a Stripe Checkout
   - **Banco General/Yappy:** Genera URL de pago
   - **Efectivo:** Marca como "awaiting_confirmation"

### 6. Verificar Estado del Pago

1. Después del pago, deberías ser redirigido a `/payments/<id>/status`
2. Verifica que muestre:
   - Estado del pago
   - Detalles del pago
   - Información del servicio
   - Si el pago fue exitoso, debería crear el appointment automáticamente

### 7. Verificar Cita Creada

1. Ve a **"Citas"** o `/appointments/`
2. Deberías ver la cita creada con:
   - Referencia única
   - Estado: "pending" (esperando confirmación del asesor)
   - Fecha y hora seleccionada
   - Descripción del caso

---

## 🔍 Verificaciones Adicionales

### Verificar en Base de Datos

```python
# Verificar servicio configurado
service = Service.query.get(1)
print(f"appointment_type_id: {service.appointment_type_id}")
print(f"deposit_percentage: {service.deposit_percentage}")

# Verificar slots disponibles
slots = AppointmentSlot.query.filter(
    AppointmentSlot.appointment_type_id == service.appointment_type_id,
    AppointmentSlot.is_available == True
).all()
print(f"Slots disponibles: {len(slots)}")

# Verificar appointments creados
appointments = Appointment.query.filter_by(service_id=1).all()
print(f"Citas creadas para este servicio: {len(appointments)}")
```

### Verificar Logs

Revisa los logs de la aplicación para ver:
- Creación de Payment
- Creación de Appointment
- Reserva de Slot
- ActivityLog registrado

---

## 🐛 Solución de Problemas

### El botón "Solicitar Cita" no aparece

**Causas posibles:**
1. El servicio no tiene `appointment_type_id` configurado
2. El servicio es gratuito (`is_free_service()` retorna True)
3. El servicio no está activo

**Solución:**
```python
# Verificar y configurar
service = Service.query.get(SERVICE_ID)
service.appointment_type_id = APPOINTMENT_TYPE_ID
service.deposit_percentage = 0.5  # 50% de abono
db.session.commit()
```

### No hay slots disponibles

**Causa:** No se han creado slots para el tipo de cita del servicio

**Solución:**
- Los asesores deben crear slots desde su dashboard
- O crear slots manualmente desde el admin

### Error al procesar el pago

**Verificar:**
1. Que Stripe esté configurado (si usas Stripe)
2. Que el método de pago seleccionado esté disponible
3. Revisar los logs de error

### La cita no se crea después del pago

**Verificar:**
1. Que el callback `/api/payments/<id>/success` se ejecute
2. Que el payment tenga `status = 'succeeded'`
3. Que el slot aún esté disponible
4. Revisar los logs de error

---

## 📊 Datos de Prueba Creados

- **Servicio:** Artículos/Revistas (ID: 1)
- **Tipo de Cita:** Asesoría técnica en configuración de MS O365 (ID: 1)
- **Asesor:** Seul Najad Hidalgo (ID: 1)
- **Slots:** 5 slots creados para los próximos días
- **Abono:** 50% del precio final

---

## 🎯 Próximos Pasos

1. **Configurar más servicios:**
   - Asignar `appointment_type_id` a otros servicios
   - Configurar abonos según necesidad

2. **Crear más slots:**
   - Los asesores pueden crear slots desde su dashboard
   - O desde el panel de administración

3. **Probar diferentes escenarios:**
   - Pago completo vs. abono
   - Diferentes métodos de pago
   - Cancelación de citas
   - Pago de saldo pendiente

---

## ✅ Checklist de Prueba

- [ ] Botón "Solicitar Cita" aparece en servicios de pago
- [ ] Formulario se carga correctamente
- [ ] Validación de descripción (50-1000 chars) funciona
- [ ] Slots disponibles se muestran correctamente
- [ ] Cálculo de abono es correcto
- [ ] Métodos de pago se muestran
- [ ] Pago se procesa correctamente
- [ ] Appointment se crea después del pago
- [ ] Slot se reserva correctamente
- [ ] Cita aparece en `/appointments/`
- [ ] ActivityLog registra la acción

---

**¡Listo para probar!** 🚀
