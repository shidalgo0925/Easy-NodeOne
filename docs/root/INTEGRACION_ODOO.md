# Integración con Odoo 18

## 📋 Descripción

Este documento explica cómo configurar la integración entre `membresia-relatic` y Odoo 18 para sincronizar automáticamente pagos confirmados.

## 🔧 Configuración

### Variables de Entorno

Agregar las siguientes variables de entorno al archivo `.env` o al sistema:

```bash
# Habilitar integración con Odoo
ODOO_INTEGRATION_ENABLED=true

# URL del endpoint de Odoo
ODOO_API_URL=https://odoo.relatic.org/api/relatic/v1/sale

# API Key (debe coincidir con la configurada en Odoo)
ODOO_API_KEY=tu_api_key_aqui

# HMAC Secret (debe coincidir con la configurada en Odoo)
ODOO_HMAC_SECRET=tu_hmac_secret_aqui

# Ambiente (prod, dev, test)
ODOO_ENVIRONMENT=prod
```

### Configuración en Odoo

1. **Instalar el módulo** `relatic_integration` en Odoo
2. **Configurar parámetros del sistema**:
   - `relatic_integration.api_key`: Debe ser el mismo valor que `ODOO_API_KEY`
   - `relatic_integration.hmac_secret`: Debe ser el mismo valor que `ODOO_HMAC_SECRET`
   - `relatic_integration.auto_create_product`: `True` o `False` (opcional)

3. **Crear diarios de pago** en Odoo:
   - YAPPY (tipo: banco)
   - TARJETA (tipo: banco)
   - TRANSFERENCIA (tipo: banco)

4. **Crear productos** con SKU:
   - MEMB-ANUAL (Membresía Anual)
   - MEMB-BASICO (Membresía Básica)
   - MEMB-PREMIUM (Membresía Premium)
   - MEMB-DELUXE (Membresía DeLuxe)

## 🔄 Flujo de Integración

1. **Cliente paga** en membresia-relatic
2. **Pago se confirma** (status = 'succeeded')
3. **Sistema envía webhook** a Odoo automáticamente
4. **Odoo procesa** el webhook y crea:
   - Contacto (si no existe)
   - Factura de cliente
   - Movimiento de pago
   - Conciliación automática

## 📤 Formato del Webhook

El sistema envía un payload JSON según el contrato v1.0:

```json
{
  "meta": {
    "version": "1.0",
    "source": "membresia-relatic",
    "environment": "prod",
    "timestamp": "2026-01-20T10:30:00Z"
  },
  "order_id": "ORD-2026-00021",
  "member": {
    "email": "usuario@email.com",
    "name": "Juan Pérez",
    "vat": "8-123-456",
    "phone": "+507-6123-4567"
  },
  "items": [
    {
      "sku": "MEMB-ANUAL",
      "name": "Membresía Anual",
      "qty": 1,
      "price": 120.00,
      "tax_rate": 7.0
    }
  ],
  "payment": {
    "method": "YAPPY",
    "amount": 128.40,
    "reference": "YAPPY-EBOWR-38807178",
    "date": "2026-01-20",
    "currency": "PAB"
  }
}
```

## 🔐 Seguridad

- **API Key**: Autenticación Bearer Token
- **HMAC Signature**: Firma del payload para prevenir manipulación
- **HTTPS**: Todas las comunicaciones son seguras

## ⚙️ Dónde se Envía el Webhook

El webhook se envía automáticamente cuando:

1. **Pago confirmado vía PayPal** (`/payment/paypal/return`)
2. **Pago confirmado vía Stripe** (webhook de Stripe)
3. **Pago confirmado manualmente** (panel admin)
4. **Pago confirmado en payment_success** (página de éxito)

## 🐛 Solución de Problemas

### El webhook no se envía

1. Verificar que `ODOO_INTEGRATION_ENABLED=true`
2. Verificar que `ODOO_API_KEY` y `ODOO_HMAC_SECRET` estén configurados
3. Revisar logs del servidor para ver errores

### Error 401 - Invalid API Key

- Verificar que `ODOO_API_KEY` en membresia-relatic coincida con `relatic_integration.api_key` en Odoo

### Error 401 - Invalid Signature

- Verificar que `ODOO_HMAC_SECRET` en membresia-relatic coincida con `relatic_integration.hmac_secret` en Odoo

### Error 422 - Product Not Found

- Verificar que el producto con el SKU correspondiente exista en Odoo
- O activar `relatic_integration.auto_create_product = True` en Odoo

### Error 422 - Journal Not Found

- Verificar que existan los diarios YAPPY, TARJETA, TRANSFERENCIA en Odoo

## 📊 Verificar Sincronización

### En membresia-relatic

Revisar logs del servidor:
```bash
tail -f /var/log/membresia-relatic/app.log | grep Odoo
```

### En Odoo

1. **Ver logs de sincronización**:
   - Menú: Contabilidad → Relatic Integration → Logs de Sincronización
   - Buscar por Order ID (ej: ORD-2026-00021)

2. **Ver facturas creadas**:
   - Menú: Contabilidad → Clientes → Facturas
   - Buscar por "Origen" = Order ID

3. **Ver contactos**:
   - Menú: Contactos → Contactos
   - Buscar por email o etiqueta "RELATIC_MIEMBRO"

## 🔍 Testing

Para probar la integración:

1. **Habilitar modo test**:
   ```bash
   ODOO_ENVIRONMENT=test
   ```

2. **Realizar un pago de prueba** en membresia-relatic

3. **Verificar logs** en ambos sistemas

4. **Verificar en Odoo** que se creó la factura

## 📝 Notas Importantes

- El webhook **no bloquea** el flujo principal si falla
- Los errores se registran en logs pero no afectan la confirmación del pago
- La integración es **idempotente**: enviar el mismo pago múltiples veces no crea duplicados
- El Order ID se genera como: `ORD-{YEAR}-{PAYMENT_ID:05d}`

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs de sincronización en Odoo
2. Revisar logs del servidor de membresia-relatic
3. Verificar configuración de variables de entorno
4. Verificar configuración en Odoo

---

**Última actualización**: 2026-01-20  
**Versión**: 1.0
