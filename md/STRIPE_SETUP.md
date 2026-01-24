# Configuración de Stripe para RelaticPanama

## Pasos para configurar Stripe

### 1. Crear cuenta en Stripe
1. Ve a [https://stripe.com](https://stripe.com)
2. Crea una cuenta gratuita
3. Completa la verificación de tu cuenta

### 2. Obtener las claves de API
1. En el dashboard de Stripe, ve a **Developers > API keys**
2. Copia las siguientes claves:
   - **Publishable key** (pk_test_...)
   - **Secret key** (sk_test_...)

### 3. Configurar las variables de entorno
Crea un archivo `.env` en la raíz del proyecto con:

```bash
# Configuración de Stripe
STRIPE_SECRET_KEY=sk_test_tu_clave_secreta_aqui
STRIPE_PUBLISHABLE_KEY=pk_test_tu_clave_publica_aqui
STRIPE_WEBHOOK_SECRET=whsec_tu_webhook_secret_aqui

# Configuración de Email (opcional)
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion
MAIL_DEFAULT_SENDER=noreply@relaticpanama.org
```

### 4. Configurar Webhooks (Opcional)
1. En Stripe Dashboard, ve a **Developers > Webhooks**
2. Crea un nuevo endpoint: `https://tu-dominio.com/stripe-webhook`
3. Selecciona el evento: `payment_intent.succeeded`
4. Copia el **Signing secret** y agrégalo a tu archivo `.env`

### 5. Probar el sistema
1. Usa las tarjetas de prueba de Stripe:
   - **Éxito**: 4242 4242 4242 4242
   - **Fallo**: 4000 0000 0000 0002
   - **Requiere autenticación**: 4000 0025 0000 3155

## Tarjetas de Prueba de Stripe

| Número | Resultado | Descripción |
|--------|-----------|-------------|
| 4242 4242 4242 4242 | Éxito | Pago exitoso |
| 4000 0000 0000 0002 | Fallo | Tarjeta rechazada |
| 4000 0025 0000 3155 | Requiere autenticación | 3D Secure |

**Fecha de vencimiento**: Cualquier fecha futura
**CVC**: Cualquier código de 3 dígitos

## Precios Configurados

- **Membresía Básica**: $75.00 USD/año
- **Membresía Premium**: $150.00 USD/año

## Funcionalidades Implementadas

✅ **Sistema de Pagos**
- Integración con Stripe
- Procesamiento de pagos con tarjetas
- Manejo de errores de pago

✅ **Gestión de Suscripciones**
- Creación automática de suscripciones
- Control de vencimiento (1 año)
- Estados de membresía

✅ **Notificaciones por Email**
- Confirmación de pago
- Detalles de la membresía
- Información de beneficios

✅ **Interfaz de Usuario**
- Página de checkout profesional
- Página de confirmación de pago
- Botones de pago en membresía

## Próximos Pasos

1. **Configurar dominio personalizado**
2. **Implementar renovaciones automáticas**
3. **Agregar más métodos de pago**
4. **Crear dashboard de administración**
5. **Implementar sistema de referidos**

## Soporte

Para cualquier problema con la configuración de Stripe, consulta:
- [Documentación de Stripe](https://stripe.com/docs)
- [Centro de ayuda de Stripe](https://support.stripe.com/)
