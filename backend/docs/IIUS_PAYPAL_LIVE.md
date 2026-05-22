# IIUS — Activar PayPal live

**Yappy:** fuera de alcance hasta que el cliente lo pida.

## Estado actual

- Matriz: **PayPal activo**; SWIFT y Yappy **desactivados**.
- `PaymentConfig` org 1: credenciales en **BD** (`use_environment_variables = false`).
- URLs de retorno ya fijadas a `BASE_URL` + `/payment/paypal/return` y `/payment/paypal/cancel`.
- Sin `client_id` / `secret` → checkout sigue en **modo demo** (válido para pruebas).

## Pasos (una vez tengan credenciales live de PayPal)

1. Entrar como admin en `https://apps.internationalinstitute.us`.
2. Menú superior → engranaje / **Pagos** (o `/admin/payments`).
3. Selector de empresa → **org IIUS (1)** → **Aplicar**.
4. Completar:
   - **Client ID** y **Client Secret** (app live en [developer.paypal.com](https://developer.paypal.com)).
   - **Modo:** `live`.
   - Confirmar URLs de retorno/cancelación (ya guardadas; deben coincidir con la app PayPal).
5. **Guardar** configuración.
6. Prueba: inscripción pública → login → checkout → PayPal (debe abrir `api-m.paypal.com`, no demo).

## Alternativa por `.env` (solo si prefieren env)

En `/opt/easynodeone/app/.env`:

```bash
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=live
PAYPAL_RETURN_URL=https://apps.internationalinstitute.us/payment/paypal/return
PAYPAL_CANCEL_URL=https://apps.internationalinstitute.us/payment/paypal/cancel
```

Y en Admin → Pagos marcar **«Usar variables de entorno»** + reiniciar `nodeone.service`.

## Checklist ítem 8

| Resultado | Cuándo |
|-----------|--------|
| Demo OK | Sin credenciales (hoy) |
| Live OK | Tras guardar credenciales y pago de prueba real |
