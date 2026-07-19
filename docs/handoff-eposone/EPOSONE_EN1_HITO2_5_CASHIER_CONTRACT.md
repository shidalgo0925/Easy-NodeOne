# EPosOne — contrato EN1 Hito 2.5: cajero POS

Estado: **v1 congelado para implementación APK**  
Responsable del contrato: EN1 backend  
Endpoint existente: `GET /api/v1/devices/bootstrap`

## 1. Decisiones obligatorias

- El dispositivo ya está provisionado a una Caja; la APK no solicita seleccionar Caja.
- El POS abre el turno en el flujo normal. Back Office conserva apertura excepcional,
  cambio de cajero, cierre de emergencia y auditoría.
- El cajero es un `en1_contact` con `is_cashier=true`, no un usuario administrador.
- EN1 nunca guarda ni entrega el PIN en texto plano.
- Toda operación POS indicada en §5 transporta `cashier_contact_id`.
- Bootstrap es también el mecanismo Sync Down. No existe un endpoint especial de cajeros.

## 2. Snapshot de cajeros

El bootstrap incluye por defecto `cashiers`. También puede solicitarse explícitamente:

```http
GET /api/v1/devices/bootstrap?include=cashiers
Authorization: Bearer <device_token>
```

Respuesta con cambios:

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-18T20:30:00Z",
  "cashiers_version": 1721334600123,
  "cashiers_changed": true,
  "cashiers_count": 2,
  "cashiers": [
    {
      "cashier_contact_id": 27,
      "cashier_name": "Juan Pérez",
      "cashier_code": "CJR-0027",
      "is_active": true,
      "pin_verifier": "pbkdf2_sha256$310000$<salt_base64url>$<hash_base64url>",
      "pin_version": 3,
      "updated_at": "2026-07-18T20:29:58.345Z"
    },
    {
      "cashier_contact_id": 31,
      "cashier_name": "Ana Mora",
      "cashier_code": "CJR-0031",
      "is_active": false,
      "pin_verifier": null,
      "pin_version": 2,
      "updated_at": "2026-07-18T18:11:02.140Z"
    }
  ]
}
```

Se envían activos e inactivos. Un cajero inactivo llega sin verificador para que la APK
revoque su acceso local.

### Sync incremental

La APK conserva `cashiers_version` y lo envía en el siguiente bootstrap:

```http
GET /api/v1/devices/bootstrap?include=cashiers&cashiers_version=1721334600123
```

Si no cambió:

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-18T20:35:00Z",
  "cashiers_version": 1721334600123,
  "cashiers_changed": false
}
```

En ese caso `cashiers` y `cashiers_count` se omiten. La versión es el máximo
`updated_at` del cajero o de su credencial, expresado en milisegundos Unix.

## 3. Verificador PIN

Formato portable:

```text
pbkdf2_sha256$310000$<salt_base64url_sin_padding>$<digest_base64url_sin_padding>
```

- KDF: PBKDF2-HMAC-SHA256.
- Iteraciones: `310000`.
- Sal aleatoria: 16 bytes.
- Digest: 32 bytes.
- PIN admitido por EN1: 4 a 8 dígitos ASCII.
- Cada cambio genera nueva sal y aumenta `pin_version`.
- El Back Office recibe el PIN únicamente en el POST TLS y persiste solo el verificador.

La APK debe guardar el catálogo cifrado con una clave protegida por Android Keystore,
comparar el digest en tiempo constante y aplicar límite de intentos/bloqueo temporal.

## 4. Sesión local

Después de validar el PIN, la APK registra localmente:

```json
{
  "cashier_contact_id": 27,
  "cashier_name": "Juan Pérez",
  "login_time": "2026-07-18T20:40:12Z",
  "pin_version": 3
}
```

La cabecera operativa muestra siempre Caja, Cajero y Turno. La autenticación local no
requiere EN1 disponible.

## 5. Sync Up de operaciones

Las siguientes operaciones requieren `cashier_contact_id` en `payload`:

- `create_order`
- `transition_order_status` (incluye cancelación)
- `capture_payment`
- `refund_payment`
- `open_cash_shift`
- `reconcile_cash_shift`
- `close_cash_shift`
- `manual_cash_movement`
- `split_order`
- `transfer_order`

Ejemplo de apertura:

```json
{
  "operation_type": "open_cash_shift",
  "payload": {
    "register_ref": "CAJA-01",
    "opening_balance": 100.0,
    "cashier_contact_id": 27,
    "login_time": "2026-07-18T20:40:12Z"
  }
}
```

EN1 rechaza `open_cash_shift` si el cajero está inactivo o no existe. Para operaciones
offline ya ocurridas, EN1 acepta un cajero existente aunque haya sido desactivado después;
la siguiente descarga obliga a la APK a revocarlo. Un ID inexistente siempre se rechaza.

La atribución queda persistida en pedido, pago, reembolso, movimiento y cierre de turno,
y en los eventos de auditoría de transición, cancelación, arqueo y transferencia.

## 6. Conflictos de turno

- La Caja solo puede tener un turno abierto.
- BO puede cambiar el cajero del turno como excepción auditada.
- Un evento offline conserva el `cashier_contact_id` que realmente lo ejecutó; no se
  reescribe con el cajero actual del turno al sincronizar.
- Si BO cerró el turno antes del Sync Up, EN1 aplica las reglas de estado existentes y
  rechaza operaciones incompatibles; la APK debe mostrarlas como conflicto, no descartarlas.

## 7. Changelog

- **v1 — 2026-07-18:** snapshot versionado, verificador PBKDF2 portable, revocación por
  cajero inactivo y atribución obligatoria de operaciones Sync Up.
