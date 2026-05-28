"""Mapper mínimo EN1 → JSON efacturapty (Fase A; ampliar en Fase B)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from models.efactura import ElectronicInvoiceProviderConfig


def build_test_invoice_payload(
    config: ElectronicInvoiceProviderConfig,
    *,
    amount: Decimal,
    description: str,
    customer_email: str,
    customer_name: str = 'CONSUMIDOR FINAL',
) -> dict[str, Any]:
    """Factura de prueba — consumidor final, una línea, ITBMS exento (00)."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    pos = (config.default_pos or '001').strip() or '001'
    amt = float(amount)
    desc = (description or 'Servicio de prueba EN1').strip()[:500]
    email = (customer_email or 'consumidor@example.com').strip()
    return {
        'datosGenerales': {
            'tipoEmision': '01',
            'tipoDocumento': '01',
            'puntoFacturacion': pos,
            'fechaEmision': now,
            'naturalezaOperacion': '01',
            'tipoOperacion': 1,
            'destinoOperacion': 1,
            'formatoGeneracionCafe': 1,
            'maneraEntregaCafe': 1,
            'envioContenedorReceptor': 1,
            'procesoGeneracionFe': 1,
            'tipoTransaccionVenta': 1,
            'tipoSucursal': 1,
            'informacionInteresEmisor': 'Prueba FE EN1 (sandbox)',
            'informacionReceptor': {
                'tipoReceptorFe': '02',
                'nombreRazonReceptor': customer_name,
                'direccionReceptor': 'Ciudad de Panama',
                'correoElectronicoReceptor': email,
                'paisReceptor': 'PA',
                'telefonoContactoReceptor': '6000-0000',
            },
        },
        'listaItems': [
            {
                'numeroSecuenciaItem': 1,
                'descripcionProductoServicio': desc,
                'codigoInternoItem': 'PRUEBA-EN1',
                'unidadMedidaCodigoInterno': 'und',
                'cantidadProductoServicio': 1,
                'grupoPrecios': {
                    'precioUnitarioTransferencia': amt,
                    'precioItem': amt,
                    'sumaPrecioItem': amt,
                },
                'grupoITBMS': {
                    'tasaITBMSAplicable': '00',
                    'montoITBMS': 0.0,
                },
            }
        ],
        'totales': {
            'tiempoPago': 1,
            'grupoFormasPago': [{'formaPago': '02', 'valorCuotaPagada': amt}],
            'totalNeto': amt,
            'totalITBMS': 0.0,
            'valorTotalFactura': amt,
            'sumaValoresRecibidos': amt,
            'numeroTotalItems': 1,
            'totalTodosItems': amt,
        },
    }
