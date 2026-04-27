# Configuración de Métodos de Pago

Este documento explica cómo configurar y gestionar los diferentes métodos de pago disponibles en el sistema de membresías **RELATIC** (Easy NodeOne).

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Acceso al Panel de Configuración](#acceso-al-panel-de-configuración)
3. [Métodos de Pago Disponibles](#métodos-de-pago-disponibles)
4. [Configuración por Método](#configuración-por-método)
5. [Variables de Entorno vs Base de Datos](#variables-de-entorno-vs-base-de-datos)
6. [Modo de Prueba vs Producción](#modo-de-prueba-vs-producción)
7. [Flujo de Configuración](#flujo-de-configuración)
8. [Estructura de la Base de Datos](#estructura-de-la-base-de-datos)
9. [API de Configuración](#api-de-configuración)
10. [Troubleshooting](#troubleshooting)
11. [Mejores Prácticas](#mejores-prácticas)
12. [Ejemplos de Uso](#ejemplos-de-uso)
13. [Recursos Adicionales](#recursos-adicionales)
14. [Changelog](#changelog)

---

## Introducción

El sistema de pagos permite configurar múltiples métodos de pago desde el panel de administración, sin necesidad de modificar código o archivos de configuración. Las credenciales pueden almacenarse en:

- **Base de datos**: Configuración gestionada desde el panel web
- **Variables de entorno**: Configuración en archivo `.env` (más seguro para producción)

---

## Acceso al Panel de Configuración

### Requisitos

- Tener permisos de administrador
- Estar autenticado en el sistema

### Pasos

1. Inicia sesión como administrador
2. Navega a: `/admin/payments`
3. Verás el panel de configuración con todos los métodos disponibles

### URL Directa

```
https://tu-dominio.com/admin/payments
```

---

## Métodos de Pago Disponibles

El sistema soporta los siguientes métodos de pago:

| Método | Tipo | Estado | Descripción |
|--------|------|--------|-------------|
| **Stripe** | API | ✅ Activo | Pagos con tarjeta de crédito/débito |
| **PayPal** | API | ✅ Activo | Pagos a través de PayPal |
| **Banco General** | API/Manual | ✅ Activo | Pagos mediante CyberSource (Banco General) |
| **Yappy** | API/Manual | ✅ Activo | Pagos mediante Yappy (Panamá) |
| **Interbank** | Manual | ✅ Activo | Transferencias bancarias (Perú) |

---

## Configuración por Método

### 1. Stripe (Tarjeta de Crédito)

Stripe es el método principal para pagos con tarjeta de crédito/débito.

#### Credenciales Necesarias

- **Secret Key**: Clave secreta de Stripe (comienza con `sk_test_` o `sk_live_`)
- **Publishable Key**: Clave pública de Stripe (comienza con `pk_test_` o `pk_live_`)
- **Webhook Secret** (Opcional): Secreto para validar webhooks (comienza con `whsec_`)

#### Cómo Obtener las Credenciales

1. Accede a [Stripe Dashboard](https://dashboard.stripe.com/)
2. Ve a **Developers > API keys**
3. Copia las claves de prueba (`test`) o producción (`live`)
4. Para webhooks, ve a **Developers > Webhooks** y crea un endpoint

#### Configuración en el Panel

```
Secret Key: sk_test_51AbCdEfGhIjKlMnOpQrStUvWxYz...
Publishable Key: pk_test_51AbCdEfGhIjKlMnOpQrStUvWxYz...
Webhook Secret: whsec_1234567890abcdef...
```

#### Variables de Entorno

```env
STRIPE_SECRET_KEY=sk_test_51AbCdEfGhIjKlMnOpQrStUvWxYz...
STRIPE_PUBLISHABLE_KEY=pk_test_51AbCdEfGhIjKlMnOpQrStUvWxYz...
STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdef...
```

---

### 2. PayPal

PayPal permite pagos mediante cuenta PayPal o tarjeta de crédito.

#### Credenciales Necesarias

- **Client ID**: ID de cliente de la aplicación PayPal
- **Client Secret**: Secreto de cliente de la aplicación PayPal
- **Modo**: `sandbox` (pruebas) o `live` (producción)
- **Return URL**: URL de retorno después del pago
- **Cancel URL**: URL de cancelación

#### Cómo Obtener las Credenciales

1. Accede a [PayPal Developer](https://developer.paypal.com/)
2. Crea una aplicación en **My Apps & Credentials**
3. Copia el **Client ID** y **Client Secret**
4. Configura las URLs de retorno en la aplicación

#### Configuración en el Panel

```
Client ID: AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
Client Secret: 1234567890AbCdEfGhIjKlMnOpQrStUvWxYz
Modo: sandbox (o live para producción)
```

**URLs de retorno (deben coincidir con el host público de la app y, si aplica, con la app en PayPal Developer):**

- **Return URL:** `https://apps.relatic.org/payment/paypal/return`
- **Cancel URL:** `https://apps.relatic.org/payment/paypal/cancel`

Si Nginx/Cloudflare también enrutan el backend en `https://miembros.relatic.org` (mismo org), esas URLs son equivalentes; lo importante es que sean **HTTPS** y apunten al **mismo** despliegue.

#### Variables de Entorno

```env
PAYPAL_CLIENT_ID=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
PAYPAL_CLIENT_SECRET=1234567890AbCdEfGhIjKlMnOpQrStUvWxYz
PAYPAL_MODE=sandbox
PAYPAL_RETURN_URL=https://apps.relatic.org/payment/paypal/return
PAYPAL_CANCEL_URL=https://apps.relatic.org/payment/paypal/cancel
```

Las credenciales **Sandbox** exigen `PAYPAL_MODE=sandbox`; **Live** exigen `PAYPAL_MODE=live` y claves de la app **Live** en [developer.paypal.com](https://developer.paypal.com/).

---

### 3. Banco General (CyberSource)

Banco General utiliza CyberSource para procesar pagos.

#### Credenciales Necesarias

- **Merchant ID**: ID del comercio en CyberSource
- **API Key**: Clave de API de CyberSource
- **Shared Secret**: Secreto compartido de CyberSource
- **API URL**: URL de la API (por defecto: `https://api.cybersource.com`)

#### Cómo Obtener las Credenciales

1. Contacta con Banco General para obtener acceso a CyberSource
2. Obtén las credenciales desde el portal de CyberSource
3. Configura el merchant ID y las claves de API

#### Configuración en el Panel

```
Merchant ID: tu_merchant_id_aqui
API Key: tu_api_key_aqui
Shared Secret: tu_shared_secret_aqui
API URL: https://api.cybersource.com
```

#### Variables de Entorno

```env
BANCO_GENERAL_MERCHANT_ID=tu_merchant_id_aqui
BANCO_GENERAL_API_KEY=tu_api_key_aqui
BANCO_GENERAL_SHARED_SECRET=tu_shared_secret_aqui
```

---

### 4. Yappy

Yappy es un método de pago móvil popular en Panamá.

#### Credenciales Necesarias

- **API Key**: Clave de API de Yappy
- **Merchant ID**: ID del comercio en Yappy
- **API URL**: URL de la API (por defecto: `https://api.yappy.im`)

#### Cómo Obtener las Credenciales

1. Regístrate en [Yappy Business](https://yappy.im/business)
2. Obtén las credenciales desde el panel de Yappy
3. Configura el merchant ID y la API key

#### Configuración en el Panel

```
API Key: tu_yappy_api_key_aqui
Merchant ID: tu_merchant_id_aqui
API URL: https://api.yappy.im
```

#### Variables de Entorno

```env
YAPPY_API_KEY=tu_yappy_api_key_aqui
YAPPY_MERCHANT_ID=tu_merchant_id_aqui
```

---

### 5. Interbank (Transferencia Manual)

Interbank es un método manual que requiere transferencia bancaria.

#### Información Necesaria

- **Cuenta de Ahorros**: Número de cuenta
- **CCI**: Código de Cuenta Interbancario
- **Titular**: Nombre del titular de la cuenta

#### Configuración

Este método no requiere credenciales API, solo información bancaria que se muestra al usuario durante el checkout.

#### Valores en pantalla (ejemplo)

**No** guardes en el repositorio datos bancarios reales. Sustituí en `checkout.html` o en la config que uses:

```
Cuenta de Ahorros: <número proporcionado por operaciones>
CCI: <CCI>
Titular: <razón social o titular>
```

**Nota:** El método se muestra de forma estática al usuario. Tras rotar o cambiar datos, actualizá el template o la base de datos y el despliegue; no versiones claves ni números de cuenta en el código.

---

## Variables de Entorno vs Base de Datos

El sistema permite elegir entre dos formas de almacenar las credenciales:

### Opción 1: Variables de Entorno (Recomendado para Producción)

**Ventajas:**
- ✅ Más seguro (no se almacenan en la base de datos)
- ✅ Fácil de gestionar con sistemas de CI/CD
- ✅ No requiere acceso al panel web para cambiar
- ✅ Mejor para múltiples entornos (dev, staging, prod)

**Desventajas:**
- ❌ Requiere acceso al servidor para modificar
- ❌ Necesita reiniciar la aplicación para aplicar cambios

**Cómo Usar:**

1. En el panel `/admin/payments`, activa el switch "Usar variables de entorno"
2. Guarda la configuración
3. Asegúrate de que las variables estén en el archivo `.env`:

```env
# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# PayPal
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=live

# Banco General
BANCO_GENERAL_MERCHANT_ID=...
BANCO_GENERAL_API_KEY=...
BANCO_GENERAL_SHARED_SECRET=...

# Yappy
YAPPY_API_KEY=...
YAPPY_MERCHANT_ID=...
```

### Opción 2: Base de Datos (Recomendado para Desarrollo)

**Ventajas:**
- ✅ Fácil de cambiar desde el panel web
- ✅ No requiere reiniciar la aplicación
- ✅ Útil para pruebas rápidas

**Desventajas:**
- ❌ Menos seguro (credenciales en la base de datos)
- ❌ Requiere acceso al panel de administración

**Cómo Usar:**

1. En el panel `/admin/payments`, desactiva el switch "Usar variables de entorno"
2. Ingresa las credenciales directamente en los campos del formulario
3. Guarda la configuración
4. Los cambios se aplican inmediatamente

---

## Modo de Prueba vs Producción

### Modo de Prueba (Demo/Sandbox)

El sistema detecta automáticamente si está en modo de prueba cuando:

- No hay credenciales configuradas
- Las credenciales son de prueba (ej: `sk_test_...`, `pk_test_...`)
- PayPal está en modo `sandbox`

**Características:**
- Los pagos se simulan automáticamente
- No se procesan transacciones reales
- Ideal para pruebas y desarrollo

**Indicadores:**
- Alerta amarilla en el checkout: "Modo de Prueba"
- Los pagos se completan automáticamente después de 2 segundos (Stripe demo)
- No se requieren tarjetas reales

### Modo Producción

El sistema entra en modo producción cuando:

- Hay credenciales reales configuradas
- Las credenciales son de producción (ej: `sk_live_...`, `pk_live_...`)
- PayPal está en modo `live`

**Características:**
- Los pagos se procesan realmente
- Se cobran tarjetas y cuentas reales
- Requiere configuración completa y correcta

**Recomendaciones:**
- Usa variables de entorno en producción
- Mantén las credenciales seguras
- Prueba primero en modo sandbox
- Monitorea los logs de pagos

---

## Flujo de Configuración

### Paso 1: Acceder al Panel

```
1. Inicia sesión como administrador
2. Ve a /admin/payments
```

### Paso 2: Elegir Fuente de Configuración

```
1. Activa/desactiva "Usar variables de entorno"
2. Si activas: configura las variables en .env
3. Si desactivas: ingresa credenciales en el formulario
```

### Paso 3: Configurar Cada Método

```
1. Completa los campos requeridos para cada método
2. Guarda la configuración
3. Verifica que no haya errores
```

### Paso 4: Probar

```
1. Ve a /checkout con productos en el carrito
2. Selecciona el método de pago
3. Completa una transacción de prueba
4. Verifica en el panel de administración que el pago se registró
```

---

## Estructura de la Base de Datos

### Tabla: `payment_config`

La configuración se almacena en la tabla `payment_config`:

```sql
CREATE TABLE payment_config (
    id INTEGER PRIMARY KEY,
    stripe_secret_key VARCHAR(500),
    stripe_publishable_key VARCHAR(500),
    stripe_webhook_secret VARCHAR(500),
    paypal_client_id VARCHAR(500),
    paypal_client_secret VARCHAR(500),
    paypal_mode VARCHAR(20) DEFAULT 'sandbox',
    paypal_return_url VARCHAR(500),
    paypal_cancel_url VARCHAR(500),
    banco_general_merchant_id VARCHAR(200),
    banco_general_api_key VARCHAR(500),
    banco_general_shared_secret VARCHAR(500),
    banco_general_api_url VARCHAR(500),
    yappy_api_key VARCHAR(500),
    yappy_merchant_id VARCHAR(200),
    yappy_api_url VARCHAR(500),
    use_environment_variables BOOLEAN DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## API de Configuración

### Obtener Configuración Actual

```http
GET /api/admin/payments/config
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
    "success": true,
    "config": {
        "id": 1,
        "stripe_publishable_key": "pk_test_...",
        "paypal_mode": "sandbox",
        "use_environment_variables": true,
        ...
    }
}
```

### Actualizar Configuración

```http
PUT /api/admin/payments/config
Content-Type: application/json
Authorization: Bearer <token>

{
    "use_environment_variables": false,
    "stripe_secret_key": "sk_test_...",
    "stripe_publishable_key": "pk_test_...",
    "paypal_client_id": "...",
    "paypal_client_secret": "...",
    "paypal_mode": "sandbox",
    ...
}
```

**Respuesta:**
```json
{
    "success": true,
    "message": "Configuración actualizada exitosamente"
}
```

---

## Troubleshooting

### Problema: "No hay métodos de pago disponibles"

**Solución:**
1. Verifica que `PAYMENT_PROCESSORS_AVAILABLE` esté en `True`
2. Revisa que el módulo `payment_processors.py` esté importado correctamente
3. Verifica los logs del servidor

### Problema: "Error al crear el pago"

**Solución:**
1. Verifica que las credenciales sean correctas
2. Asegúrate de que el método esté configurado correctamente
3. Revisa los logs del procesador de pago
4. Verifica que las URLs de retorno (PayPal) sean correctas

### Problema: PayPal — "no está configurado" u OAuth / token

**Causa habitual:** faltan `PAYPAL_CLIENT_ID` y `PAYPAL_CLIENT_SECRET`, o **Sandbox vs Live** no coincide con el tipo de credenciales, o quedó un Client Secret **viejo** en la base de datos (Admin → Pagos) mientras usás variables de entorno, o al revés.

**Solución:**
1. Revisar en [developer.paypal.com](https://developer.paypal.com/) la app correcta (Sandbox o Live) y el **nuevo** Client Secret si lo rotaste.
2. Alinear `PAYPAL_MODE` con esa app.
3. Si usás "Usar variables de entorno" en el panel, definí las claves en `.env` y reiniciá el servicio.
4. Si no, borrá credenciales en conflicto en el panel o desactivá duplicados en `payment_config` para un solo origen (env **o** BD).

Si el OAuth falla, el backend puede tratarlo como **modo demo** para no bloquear el flujo; los logs del servidor lo indican.

### Problema: "Modo demo siempre activo"

**Solución:**
1. Verifica que las credenciales sean de producción (no `sk_test_...`)
2. Asegúrate de que PayPal esté en modo `live`
3. Revisa que las variables de entorno estén configuradas si usas esa opción

### Problema: "Las credenciales no se guardan"

**Solución:**
1. Verifica que tengas permisos de administrador
2. Revisa que la tabla `payment_config` exista en la base de datos
3. Ejecuta la migración: `python migrate_payment_config.py`
4. Verifica los logs del servidor para errores

### Problema: "Webhook de Stripe no funciona"

**Solución:**
1. Verifica que el `STRIPE_WEBHOOK_SECRET` esté configurado
2. Asegúrate de que la URL del webhook sea accesible públicamente
3. Verifica que el endpoint `/webhook/stripe` esté configurado
4. Revisa los logs del webhook en Stripe Dashboard

---

## Mejores Prácticas

### Seguridad

1. ✅ **Nunca** commits credenciales en el repositorio
2. ✅ Usa variables de entorno en producción
3. ✅ Rota las credenciales periódicamente
4. ✅ Usa diferentes credenciales para dev/staging/prod
5. ✅ Limita el acceso al panel de administración

### Configuración

1. ✅ Prueba primero en modo sandbox
2. ✅ Verifica cada método antes de activarlo en producción
3. ✅ Mantén un backup de la configuración
4. ✅ Documenta cualquier cambio en las credenciales
5. ✅ Monitorea los pagos regularmente

### Mantenimiento

1. ✅ Revisa los logs de pagos semanalmente
2. ✅ Verifica que los webhooks funcionen correctamente
3. ✅ Actualiza las credenciales cuando expiren
4. ✅ Prueba los métodos de pago después de actualizaciones
5. ✅ Mantén actualizada la documentación

---

## Ejemplos de Uso

### Ejemplo 1: Configurar Stripe en Producción

```bash
# 1. Configurar variables de entorno
echo "STRIPE_SECRET_KEY=sk_live_51..." >> .env
echo "STRIPE_PUBLISHABLE_KEY=pk_live_51..." >> .env

# 2. En el panel /admin/payments
# - Activar "Usar variables de entorno"
# - Guardar configuración

# 3. Reiniciar la aplicación (el nombre del unit depende del servidor)
# systemctl restart easynodeone-relatic
# systemctl restart relatic-app
```

### Ejemplo 2: Cambiar PayPal de Sandbox a Live

```bash
# 1. Obtener credenciales de producción desde PayPal Developer

# 2. En el panel /admin/payments
# - Desactivar "Usar variables de entorno"
# - Ingresar Client ID y Client Secret de producción
# - Cambiar "Modo" de "sandbox" a "live"
# - Guardar configuración
```

### Ejemplo 3: Agregar Nuevo Método de Pago

```python
# 1. Agregar al diccionario PAYMENT_METHODS en payment_processors.py
PAYMENT_METHODS = {
    ...
    'nuevo_metodo': 'Nuevo Método de Pago'
}

# 2. Crear procesador en payment_processors.py
class NuevoMetodoProcessor(PaymentProcessor):
    ...

# 3. Agregar campos a PaymentConfig en app.py
nuevo_metodo_api_key = db.Column(db.String(500))

# 4. Agregar al template admin/payments.html
# 5. Ejecutar migración de base de datos
```

---

## Recursos Adicionales

### Documentación Oficial

- [Stripe Documentation](https://stripe.com/docs)
- [PayPal Developer Documentation](https://developer.paypal.com/docs)
- [CyberSource Documentation](https://developer.cybersource.com/)
- [Yappy API Documentation](https://yappy.im/docs)

### Soporte

- **Email**: [soporte@relaticpanama.org](mailto:soporte@relaticpanama.org)
- **Panel de administración:** `/admin/payments`
- **Logs:** revisar el servicio de la aplicación en el servidor

---

## Changelog

### Versión 1.0.0

- Implementación inicial del sistema de configuración de pagos
- Soporte para Stripe, PayPal, Banco General, Yappy, Interbank
- Panel de administración web
- Soporte para variables de entorno y base de datos
- Modo demo automático

### Versión 1.1.0 (2026-04)

- Enfoque RELATIC; URLs de ejemplo de PayPal alineadas a `apps.relatic.org`
- Aclaración env vs base de datos y **Sandbox / Live** para PayPal
- Troubleshooting ampliado (OAuth PayPal, rotación de secret)
- Sección Interbank: solo placeholders; **no** se documentan datos bancarios reales en el repo

---

**Última actualización:** abril de 2026

**Versión del documento:** 1.1.0

