# Prueba aislada — efacturapty API (EN1)

**No integra** ventas, checkout, pagos ni modelos de EN1. Solo valida conectividad y emisión FE.

## Confirmado en servidor (2026-05-28)

| Ítem | Valor |
|------|--------|
| URL base | `https://api.efacturapty.com` |
| Endpoint emisión | `POST /api/v1/Invoices` |
| Auth | `Authorization: Bearer <token>` (token de aplicación del panel) |
| Header obligatorio | `Accept-Language: es-PA` |
| Ambiente | El token/emisor responde con `iAmb: 2` (pruebas DGI) |
| Query opcional | `?xml=true&qr=true` |
| Emisor | Lo completa efacturapty según el token (no hace falta repetir RUC emisor en JSON mínimo) |

OAuth2 (`sec.efacturapty.com`) existe en Swagger para otros flujos; el **token de API del panel** funciona como Bearer.

Documentación: https://www.efacturapty.com/docs · Swagger: https://api.efacturapty.com/swagger/v1/swagger.json

## Variables de entorno

```bash
export EFACTURA_API_TOKEN="tu_token"
# opcional:
export EFACTURA_API_BASE_URL="https://api.efacturapty.com"
export EFACTURA_INCLUDE_XML=1
export EFACTURA_INCLUDE_QR=1
```

**No** commitear el token. Rotar si se expuso en chat o logs.

## Ejecutar

```bash
cd /opt/easynodeone/dev/app/backend/nodeone/devtools/efacturapty_test
/opt/easynodeone/dev/venv/bin/pip install requests  # si falta
export EFACTURA_API_TOKEN="..."
/opt/easynodeone/dev/venv/bin/python test_emit_invoice.py
```

Artefactos en `captures/emit_invoice_<timestamp>.json` (request + response).

## Payload mínimo validado

Ver `factura_prueba.json`:

- Consumidor final (`tipoReceptorFe`: `02`)
- `paisReceptor`: `PA`, `correoElectronicoReceptor` obligatorio
- 1 ítem, ITBMS exento (`tasaITBMSAplicable`: `00`)
- `grupoFormasPago` con al menos un elemento (`formaPago`: `02`)
- `fechaEmision` se reemplaza en runtime por UTC

Respuesta exitosa de prueba: `autorizada: true`, `cufe` presente, `dMsgRes`: «Autorizado el uso de la FE».

## Ajustar contra factura manual del panel

1. Emitir una FE de prueba en el panel efacturapty.
2. Exportar JSON o copiar desde Postman/Swagger.
3. Reemplazar `factura_prueba.json` (mantener receptor PA + ítems + totales coherentes).
4. Volver a ejecutar el script.

## Entregables (checklist Fase 8)

- [x] Payload JSON final → `factura_prueba.json`
- [x] Script que guarda response → `test_emit_invoice.py` + `captures/`
- [x] URL base y auth documentados en este README
- [ ] Captura pantalla panel (manual)
- [ ] CUFE de la corrida que el equipo considere oficial (cada ejecución genera secuencia nueva)

## Módulo EN1 (Fase A)

La integración multitenant vive en `backend/nodeone/modules/efactura/`:

- Admin → **Fact. electrónica** (requiere módulo SaaS `efactura` ON por org)
- Plan: `docs/PLAN_MODULO_EFACTURA_EN1.md` · Fases: `docs/efactura/`

Este devtool sigue siendo útil para probar payloads sin levantar Flask.

## No hacer aún (post Fase A)

Integración checkout/pagos automática, NCR/ND, reintentos async avanzados.
