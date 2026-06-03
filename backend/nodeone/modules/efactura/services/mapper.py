"""Mapper mínimo EN1 → JSON efacturapty (Fase A; ampliar en Fase B)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from models.contact import Contact
from models.efactura import ElectronicInvoiceProviderConfig
from models.saas import TenantCrmContact
from nodeone.modules.accounting.models import Invoice, InvoiceLine, Tax
from nodeone.modules.contacts.invoice_integration import (
    contact_itbms_exempt,
    contact_receptor_block,
)
from nodeone.services.commercial_partner_service import display_name, fiscal_email as crm_fiscal_email


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


def _receptor_block(contact: Contact | TenantCrmContact) -> dict[str, Any]:
    if isinstance(contact, Contact):
        return contact_receptor_block(contact)
    ptype = (contact.person_type or 'natural').strip()
    email = crm_fiscal_email(contact) or 'consumidor@example.com'
    addr = (contact.fiscal_address or 'Ciudad de Panama').strip()[:500]
    phone = (contact.fiscal_phone or contact.phone or '6000-0000').strip()[:30]
    name = display_name(contact)[:200]
    if ptype == 'final_consumer' or not (contact.tax_id or '').strip():
        return {
            'tipoReceptorFe': '02',
            'nombreRazonReceptor': name or 'CONSUMIDOR FINAL',
            'direccionReceptor': addr,
            'correoElectronicoReceptor': email,
            'paisReceptor': (contact.country_code or 'PA')[:8],
            'telefonoContactoReceptor': phone,
        }
    block: dict[str, Any] = {
        'tipoReceptorFe': '01',
        'nombreRazonReceptor': name,
        'direccionReceptor': addr,
        'correoElectronicoReceptor': email,
        'paisReceptor': (contact.country_code or 'PA')[:8],
        'telefonoContactoReceptor': phone,
        'datosRucReceptor': {
            'tipoContribuyente': '2' if ptype == 'juridica' else '1',
            'numeroRuc': (contact.tax_id or '').strip(),
            'digitoVerificador': (contact.tax_dv or '').strip() or None,
        },
    }
    return block


def _contact_fiscal_exempt(contact: Contact | TenantCrmContact) -> bool:
    if isinstance(contact, Contact):
        return contact_itbms_exempt(contact)
    return bool(getattr(contact, 'itbms_exempt', False))


def _itbms_code_for_line(
    line: InvoiceLine,
    contact: Contact | TenantCrmContact,
    *,
    tax: Tax | None = None,
) -> str:
    if _contact_fiscal_exempt(contact):
        return '00'
    tax_amt = float(line.total or 0) - float(line.subtotal or 0)
    if tax_amt <= 0.001:
        return '00'
    rate = float(getattr(tax, 'percentage', 0) or 0) if tax is not None else 0.0
    if rate <= 0 and float(line.subtotal or 0) > 0:
        rate = round(tax_amt / float(line.subtotal) * 100.0)
    if rate >= 14:
        return '03'
    if rate >= 9:
        return '02'
    return '01'


def _line_fe_pricing(
    ln: InvoiceLine,
    contact: Contact | TenantCrmContact,
    *,
    tax: Tax | None = None,
) -> tuple[float, float, float, str, float]:
    """
    Retorna (qty, unit, line_amount, itbms_code, itbms_amt) para efacturapty.

    El PAC efacturapty rechaza líneas con ITBMS desglosado (cód. 2056/2152).
    Las líneas gravadas se envían con precio bruto (total EN1) y tasa 00.
    """
    qty = float(ln.quantity or 0)
    unit = float(ln.price_unit or 0)
    line_sub = float(ln.subtotal or qty * unit)
    line_total = float(ln.total or line_sub)
    itbms_amt = max(line_total - line_sub, 0.0)
    code = _itbms_code_for_line(ln, contact, tax=tax)
    if _contact_fiscal_exempt(contact) or itbms_amt > 0.001:
        code = '00'
        itbms_amt = 0.0
        line_amount = line_total
        unit = line_amount / qty if qty else unit
    else:
        line_amount = line_sub
    return qty, unit, line_amount, code, itbms_amt


def build_invoice_payload(
    config: ElectronicInvoiceProviderConfig,
    invoice: Invoice,
    lines: list[InvoiceLine],
    contact: Contact | TenantCrmContact,
) -> dict[str, Any]:
    """Mapper factura comercial EN1 → JSON efacturapty."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    pos = (config.default_pos or '001').strip() or '001'
    items: list[dict[str, Any]] = []
    seq = 0
    total_neto = 0.0
    total_itbms = 0.0
    tax_ids = {int(ln.tax_id) for ln in lines if ln.tax_id}
    tax_by_id: dict[int, Tax] = {}
    if tax_ids:
        for row in Tax.query.filter(Tax.id.in_(tax_ids)).all():
            tax_by_id[int(row.id)] = row
    for ln in lines:
        raw = str(ln.description or '')
        if raw.startswith('__NOTE__ '):
            continue
        seq += 1
        tax = tax_by_id.get(int(ln.tax_id)) if ln.tax_id else None
        qty, unit, line_amount, code, itbms_amt = _line_fe_pricing(ln, contact, tax=tax)
        if qty <= 0:
            continue
        unit_price = round(line_amount / qty if qty else unit, 4)
        total_neto += line_amount
        total_itbms += itbms_amt
        items.append(
            {
                'numeroSecuenciaItem': seq,
                'descripcionProductoServicio': raw.replace('__NOTE__ ', '')[:500],
                'codigoInternoItem': f'INV-{invoice.id}-{seq}',
                'unidadMedidaCodigoInterno': 'und',
                'cantidadProductoServicio': qty,
                'grupoPrecios': {
                    'precioUnitarioTransferencia': unit_price,
                    'precioItem': unit_price,
                    'sumaPrecioItem': round(line_amount, 2),
                },
                'grupoITBMS': {
                    'tasaITBMSAplicable': code,
                    'montoITBMS': round(itbms_amt, 2),
                },
            }
        )
    if not items:
        raise ValueError('La factura no tiene líneas facturables para FE.')
    grand = round(total_neto + total_itbms, 2)
    inv_grand = round(float(invoice.grand_total or 0), 2)
    if inv_grand > 0 and abs(grand - inv_grand) > 0.02:
        grand = inv_grand
        total_neto = inv_grand if total_itbms <= 0.001 else round(inv_grand - total_itbms, 2)
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
            'informacionInteresEmisor': f'Factura EN1 {invoice.number}',
            'informacionReceptor': _receptor_block(contact),
        },
        'listaItems': items,
        'totales': {
            'tiempoPago': 1,
            'grupoFormasPago': [{'formaPago': '02', 'valorCuotaPagada': grand}],
            'totalNeto': round(total_neto, 2),
            'totalITBMS': round(total_itbms, 2),
            'valorTotalFactura': grand,
            'sumaValoresRecibidos': grand,
            'numeroTotalItems': len(items),
            'totalTodosItems': grand,
        },
    }
