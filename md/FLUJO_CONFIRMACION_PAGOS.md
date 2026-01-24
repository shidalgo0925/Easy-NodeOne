# 🔄 Flujo de Confirmación de Pagos - Yappy, PayPal y Stripe (TCR)

Este documento explica cómo funciona el sistema de confirmación automática de pagos para los tres métodos principales.

---

## 📋 Flujo General (Igual para todos)

### 1. **Creación del Pago** (`create_payment_intent`)
```
Usuario → Checkout → Selecciona método de pago
↓
Backend crea Payment en BD con status='pending'
↓
Backend crea orden/pago en el proveedor (Yappy/PayPal/Stripe)
↓
Backend retorna payment_url al frontend
↓
Usuario es redirigido al proveedor para pagar
```

### 2. **Procesamiento del Pago** (Webhook Automático)
```
Usuario completa pago en proveedor
↓
Proveedor procesa el pago
↓
Proveedor llama POST /webhook/{método} automáticamente
↓
Sistema busca Payment por payment_reference
↓
Sistema valida monto y referencia
↓
Sistema actualiza Payment.status = 'succeeded'
↓
Sistema llama process_cart_after_payment()
↓
Sistema limpia carrito y activa membresía
↓
Sistema envía notificaciones al usuario
```

### 3. **Callback de Retorno** (Solo muestra estado)
```
Usuario regresa del proveedor
↓
Proveedor redirige a /payment/{método}/return
↓
Sistema busca Payment por payment_id o payment_reference
↓
Sistema verifica estado (pero webhook ya procesó todo)
↓
Sistema redirige a payment_success o checkout según estado
```

---

## 🟢 Yappy - Flujo Detallado

### **Paso 1: Creación del Pago**
```python
# En create_payment_intent() cuando payment_method='yappy'
processor = YappyProcessor(config)
success, payment_data, error = processor.create_payment(amount, currency, metadata)

# payment_data contiene:
{
    'payment_reference': 'YAPPY-XXXXXXXX',  # Referencia interna
    'yappy_transaction_id': '...',         # ID de Yappy (si API disponible)
    'payment_url': 'https://yappy.im/...', # URL de pago
    'manual': False                         # Si API no disponible, manual=True
}

# Payment se guarda en BD:
Payment(
    payment_method='yappy',
    payment_reference='YAPPY-XXXXXXXX',
    status='pending',
    payment_url='https://yappy.im/...'
)
```

### **Paso 2: Webhook Automático** (`/webhook/yappy`)
```python
# Yappy llama POST /webhook/yappy cuando confirma el pago
@app.route('/webhook/yappy', methods=['POST'])
def yappy_webhook():
    # 1. Verificar firma (si está configurada)
    signature = request.headers.get('X-Yappy-Signature')
    # ... verificación HMAC ...
    
    # 2. Extraer datos
    transaction_id = data.get('transactionId')
    payment_reference = data.get('reference')
    status = data.get('status')  # APPROVED, PAID, COMPLETED
    
    # 3. Buscar Payment
    payment = Payment.query.filter_by(
        payment_method='yappy',
        payment_reference=payment_reference  # o transaction_id
    ).first()
    
    # 4. Validar monto
    # ... comparar webhook_amount con payment.amount ...
    
    # 5. Actualizar estado
    if status in ['APPROVED', 'PAID', 'COMPLETED']:
        payment.status = 'succeeded'
        payment.paid_at = datetime.utcnow()
        db.session.commit()
        
        # 6. Procesar carrito
        cart = get_or_create_cart(payment.user_id)
        process_cart_after_payment(cart, payment)
        # ✅ Carrito limpiado, membresía activada
        
        # 7. Enviar notificaciones
        NotificationEngine.notify_membership_payment(user, payment, subscription)
    
    return jsonify({'success': True}), 200
```

### **Paso 3: Callback de Retorno** (`/payment/yappy/return`)
```python
# Usuario regresa de Yappy
@app.route('/payment/yappy/return', methods=['GET'])
def yappy_return():
    payment_id = request.args.get('payment_id')
    transaction_id = request.args.get('transaction_id')
    
    # Buscar Payment
    payment = Payment.query.get(payment_id)
    
    # Actualizar transaction_id si viene de Yappy
    if transaction_id:
        payment.payment_reference = transaction_id
    
    # Mostrar estado (webhook ya procesó todo)
    if payment.status == 'succeeded':
        return redirect(url_for('payment_success', payment_id=payment.id))
    else:
        flash('Pago pendiente...', 'info')
        return redirect(url_for('checkout'))
```

### **Características Especiales de Yappy:**
- ✅ Webhook automático cuando Yappy confirma el pago
- ✅ Verificación manual disponible (`/api/payments/yappy/verify`)
- ✅ Verificación por código de comprobante (`/api/payments/yappy/verify-by-code`)
- ✅ Verificación masiva de pendientes (`/api/payments/yappy/verify-all`)

---

## 🔵 PayPal - Flujo Detallado

### **Paso 1: Creación del Pago**
```python
# En create_payment_intent() cuando payment_method='paypal'
processor = PayPalProcessor(config)
success, payment_data, error = processor.create_payment(amount, currency, metadata)

# payment_data contiene:
{
    'payment_reference': 'ORDER_ID_DE_PAYPAL',  # Order ID de PayPal
    'payment_url': 'https://www.paypal.com/...', # URL de aprobación
    'order_data': {...}                          # Datos completos de la orden
}

# Payment se guarda en BD:
Payment(
    payment_method='paypal',
    payment_reference='ORDER_ID_DE_PAYPAL',
    status='pending',
    payment_url='https://www.paypal.com/...'
)
```

### **Paso 2: Webhook Automático** (`/webhook/paypal`) ⚠️ **NUEVO**
```python
# PayPal llama POST /webhook/paypal cuando confirma el pago
@app.route('/webhook/paypal', methods=['POST'])
def paypal_webhook():
    # 1. Verificar firma (opcional, requiere configuración)
    signature = request.headers.get('Paypal-Transmission-Sig')
    # ... verificación ...
    
    # 2. Extraer datos
    event_type = data.get('event_type')  # PAYMENT.CAPTURE.COMPLETED, etc.
    resource = data.get('resource', {})
    order_id = resource.get('id')  # Order ID de PayPal
    status = resource.get('status')  # COMPLETED, APPROVED, etc.
    
    # 3. Buscar Payment
    payment = Payment.query.filter_by(
        payment_method='paypal',
        payment_reference=order_id
    ).first()
    
    # 4. Validar monto
    # ... comparar amount_value con payment.amount ...
    
    # 5. Actualizar estado
    if event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.COMPLETED']:
        payment.status = 'succeeded'
        payment.paid_at = datetime.utcnow()
        db.session.commit()
        
        # 6. Procesar carrito
        cart = get_or_create_cart(payment.user_id)
        process_cart_after_payment(cart, payment)
        # ✅ Carrito limpiado, membresía activada
        
        # 7. Enviar notificaciones
        NotificationEngine.notify_membership_payment(user, payment, subscription)
    
    return jsonify({'success': True}), 200
```

### **Paso 3: Callback de Retorno** (`/payment/paypal/return`)
```python
# Usuario regresa de PayPal
@app.route('/payment/paypal/return', methods=['GET'])
def paypal_return():
    token = request.args.get('token')  # Order ID de PayPal
    payment_id = request.args.get('payment_id')
    
    # Buscar Payment
    payment = Payment.query.filter_by(
        payment_reference=token,
        payment_method='paypal'
    ).first()
    
    # Actualizar payment_reference si no estaba guardado
    if payment.payment_reference != token:
        payment.payment_reference = token
    
    # Verificar estado (fallback si webhook no procesó)
    if payment.status != 'succeeded':
        processor = get_payment_processor('paypal', config)
        success, status, _ = processor.verify_payment(token)
        if status == 'succeeded':
            # Procesar ahora (fallback)
            payment.status = 'succeeded'
            process_cart_after_payment(cart, payment)
    
    # Mostrar estado
    if payment.status == 'succeeded':
        return redirect(url_for('payment_success', payment_id=payment.id))
    else:
        flash('Pago pendiente...', 'info')
        return redirect(url_for('checkout'))
```

### **Características Especiales de PayPal:**
- ✅ Webhook automático cuando PayPal confirma el pago (**NUEVO**)
- ✅ Verificación manual disponible (`/api/payments/paypal/verify`)
- ✅ Verificación por payment_id (`/api/payments/paypal/verify-by-payment-id`)
- ⚠️ **Configuración requerida**: Configurar webhook en PayPal Developer Dashboard

---

## 💳 Stripe (TCR) - Flujo Detallado

### **Paso 1: Creación del Pago**
```python
# En create_payment_intent() cuando payment_method='stripe'
processor = StripeProcessor(config)
success, payment_data, error = processor.create_payment(amount, currency, metadata)

# payment_data contiene:
{
    'payment_reference': 'pi_xxxxx',      # Payment Intent ID
    'client_secret': 'pi_xxxxx_secret_xxx', # Secret para frontend
    'payment_url': None                   # Stripe se maneja en frontend
}

# Payment se guarda en BD:
Payment(
    payment_method='stripe',
    payment_reference='pi_xxxxx',
    stripe_payment_intent_id='pi_xxxxx',
    status='pending'
)
```

### **Paso 2: Procesamiento en Frontend**
```javascript
// Frontend usa Stripe.js para procesar el pago
const {error, paymentIntent} = await stripe.confirmCardPayment(clientSecret, {
    payment_method: {
        card: cardElement,
        billing_details: {...}
    }
});

// Si éxito, redirige a /payment-success
```

### **Paso 3: Verificación Manual** (No hay webhook activo)
```python
# El sistema verifica el estado cuando el usuario regresa
# Stripe webhook está deshabilitado actualmente
# Se puede activar en /stripe-webhook si se necesita
```

---

## 🔍 Comparación de Métodos

| Característica | Yappy | PayPal | Stripe (TCR) |
|---------------|-------|--------|--------------|
| **Webhook Automático** | ✅ Sí | ✅ Sí (NUEVO) | ❌ No (deshabilitado) |
| **Callback de Retorno** | ✅ Sí | ✅ Sí | ✅ Sí |
| **Verificación Manual** | ✅ Sí | ✅ Sí | ✅ Sí |
| **Procesamiento Automático** | ✅ Sí | ✅ Sí | ⚠️ Manual |
| **Referencia Interna** | `YAPPY-XXXXXXXX` | `ORDER_ID` | `pi_xxxxx` |
| **Estado Inicial** | `pending` | `pending` | `pending` |
| **Estado Final** | `succeeded` | `succeeded` | `succeeded` |

---

## ⚙️ Configuración Requerida

### **Yappy:**
- ✅ Ya configurado
- Webhook URL: `https://miembros.relatic.org/webhook/yappy`
- Secret: `YAPPY_WEBHOOK_SECRET` (opcional)

### **PayPal:** ⚠️ **CONFIGURAR**
1. Ir a [PayPal Developer Dashboard](https://developer.paypal.com/)
2. Seleccionar tu App
3. Ir a "Webhooks"
4. Agregar webhook:
   - **URL**: `https://miembros.relatic.org/webhook/paypal`
   - **Eventos**:
     - `PAYMENT.CAPTURE.COMPLETED`
     - `CHECKOUT.ORDER.COMPLETED`
5. Guardar y copiar el Webhook ID

### **Stripe:**
- ⚠️ Webhook deshabilitado actualmente
- Se puede activar en `/stripe-webhook` si se necesita

---

## 🛠️ Verificación Manual de Pagos Pendientes

### **Yappy:**
```bash
# Verificar un pago específico
curl -X POST https://miembros.relatic.org/api/payments/yappy/verify \
  -H "Content-Type: application/json" \
  -d '{"reference": "YAPPY-XXXXXXXX"}'

# Verificar todos los pendientes
curl -X POST https://miembros.relatic.org/api/payments/yappy/verify-all
```

### **PayPal:**
```bash
# Verificar un pago específico por order_id
curl -X POST https://miembros.relatic.org/api/payments/paypal/verify \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORDER_ID_DE_PAYPAL"}'

# Verificar por payment_id (requiere login)
curl -X POST https://miembros.relatic.org/api/payments/paypal/verify-by-payment-id \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"payment_id": 123}'
```

---

## 📝 Logs y Debugging

Todos los métodos tienen logging detallado:

- `📥 Webhook recibido` - Cuando llega un webhook
- `✅ Pago confirmado` - Cuando se procesa exitosamente
- `⚠️ Pago no encontrado` - Cuando no se encuentra el pago
- `❌ Error` - Cuando hay un error

Revisar logs del servidor para debugging:
```bash
tail -f /var/log/app.log | grep -E "(Webhook|PayPal|Yappy|Payment)"
```

---

## ✅ Checklist de Implementación

- [x] Webhook de Yappy funcionando
- [x] Webhook de PayPal implementado
- [x] Callbacks de retorno mejorados
- [x] Verificación manual para PayPal
- [x] Logging detallado
- [ ] **Configurar webhook en PayPal Developer Dashboard** ⚠️
- [ ] Probar flujo completo de PayPal
- [ ] Verificar pagos pendientes existentes

---

**Última actualización**: Enero 2025  
**Versión**: 1.0
