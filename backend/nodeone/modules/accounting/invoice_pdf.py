"""Factura visual EN1 (PDF). Representa totales persistidos; no recalcula fiscal ni emite FE."""

from __future__ import annotations

import os
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.catalog import Service
from models.contact import Contact
from models.saas import OrganizationSettings, SaasOrganization, TenantCrmContact
from models.users import User
from nodeone.core.regional_format import (
    RegionalFormatService,
    format_date_from_cfg,
    format_datetime_from_cfg,
    format_money_from_cfg,
    format_plain_number,
)
from nodeone.modules.accounting.models import Invoice, InvoiceLine
from nodeone.modules.contacts.invoice_integration import fiscal_display_name, get_invoice_fiscal_contact
from nodeone.modules.efactura.services.fe_visual import (
    find_latest_fe_for_invoice,
    fiscal_banner_text,
    resolve_qr_payload,
    should_show_fiscal_qr,
)
from nodeone.services.tenant_email_logo_storage import resolve_tenant_logo_static_relpath

NAVY = colors.HexColor('#1a3dcc')
INK = colors.HexColor('#111827')
MUTED = colors.HexColor('#4b5563')
LINE = colors.HexColor('#d1d5db')
BG = colors.HexColor('#f3f4f6')
TOTAL_BG = colors.HexColor('#1e3a8a')

_STATUS_LABEL = {
    'draft': 'Borrador',
    'posted': 'Contabilizada',
    'partial': 'Pago parcial',
    'paid': 'Pagada',
    'cancelled': 'Cancelada',
}


def _e(s) -> str:
    return escape(str(s) if s is not None else '', {'"': '&quot;', "'": '&apos;'})


def _cfg_dict(organization_id: int) -> dict[str, Any]:
    dto = RegionalFormatService.get(organization_id)
    return dto.to_dict() if dto is not None else {}


def _money(value, cfg) -> str:
    return format_money_from_cfg(value, cfg or None)


def _qty(value, cfg) -> str:
    decimals = 2
    if isinstance(cfg, dict) and cfg.get('qty_decimals') is not None:
        decimals = int(cfg.get('qty_decimals'))
    nf = (cfg or {}).get('number_format') if isinstance(cfg, dict) else '1,234.56'
    return format_plain_number(value, number_format=str(nf or '1,234.56'), decimals=decimals)


def _logo_path(organization_id: int) -> str | None:
    row = OrganizationSettings.query.filter_by(organization_id=int(organization_id)).first()
    if row is None:
        row = OrganizationSettings.query.first()
    stored = (getattr(row, 'logo_url', None) or '').strip() if row else ''
    rel = resolve_tenant_logo_static_relpath(stored).lstrip('/')
    if not rel:
        return None
    import app as app_mod

    static_root = os.path.normpath(os.path.join(os.path.dirname(app_mod.__file__), '..', 'static'))
    abs_path = os.path.join(static_root, rel.replace('/', os.sep))
    if os.path.isfile(abs_path) and abs_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return abs_path
    return None


def _qr_image_flowable(png_bytes: bytes | None, payload: str | None):
    data = png_bytes
    if not data and payload:
        import qrcode

        qr = qrcode.QRCode(border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        data = buf.getvalue()
    if not data:
        return None
    bio = BytesIO(data)
    flow = Image(bio, width=3.4 * cm, height=3.4 * cm)
    flow.hAlign = 'CENTER'
    return flow


def build_invoice_visual_context(invoice: Invoice, *, fe=None, org=None, customer=None, lines=None, cfg=None) -> dict[str, Any]:
    """Modelo de la factura visual. Tests y PDF usan la misma fuente."""
    cfg = cfg if cfg is not None else _cfg_dict(invoice.organization_id)
    org = org or SaasOrganization.query.get(invoice.organization_id)
    legal = (getattr(org, 'legal_name', None) or '').strip() if org else ''
    trade = (getattr(org, 'name', None) or '').strip() if org else ''
    paid = float(getattr(invoice, 'amount_paid', 0) or 0)
    grand = float(invoice.grand_total or 0)
    due = round(max(grand - paid, 0.0), 2)
    sub = float(invoice.total or 0)
    tax = float(invoice.tax_total or 0)
    disc = round(sub + tax - grand, 2)
    if disc < 0.005:
        disc = 0.0
    banner = fiscal_banner_text(fe)
    show_qr = should_show_fiscal_qr(fe)
    img, payload, source = resolve_qr_payload(fe) if show_qr else (None, None, None)
    return {
        'organization_id': invoice.organization_id,
        'org_legal_name': legal or trade or 'Organización',
        'org_trade_name': trade if trade and trade != legal else '',
        'org_tax_id': (getattr(org, 'tax_id', None) or '').strip() if org else '',
        'org_address': (getattr(org, 'fiscal_address', None) or '').strip() if org else '',
        'org_city': (getattr(org, 'fiscal_city', None) or '').strip() if org else '',
        'org_state': (getattr(org, 'fiscal_state', None) or '').strip() if org else '',
        'org_country': (getattr(org, 'fiscal_country', None) or '').strip() if org else '',
        'org_phone': (getattr(org, 'fiscal_phone', None) or '').strip() if org else '',
        'org_email': (getattr(org, 'fiscal_email', None) or '').strip() if org else '',
        'number': invoice.number,
        'date_label': format_date_from_cfg(invoice.date, cfg),
        'due_label': format_date_from_cfg(getattr(invoice, 'due_date', None), cfg),
        'invoice_status': _STATUS_LABEL.get((invoice.status or '').lower(), invoice.status or ''),
        'customer_name': customer.get('name') if isinstance(customer, dict) else (customer or ''),
        'customer_tax_id': customer.get('tax_id') if isinstance(customer, dict) else '',
        'customer_dv': customer.get('dv') if isinstance(customer, dict) else '',
        'customer_address': customer.get('address') if isinstance(customer, dict) else '',
        'customer_phone': customer.get('phone') if isinstance(customer, dict) else '',
        'customer_email': customer.get('email') if isinstance(customer, dict) else '',
        'subtotal': sub,
        'tax_total': tax,
        'discount': disc,
        'grand_total': grand,
        'amount_paid': paid,
        'amount_due': due,
        'show_qr': show_qr,
        'qr_payload': payload,
        'qr_image_bytes': img,
        'qr_source': source,
        'fe_status': getattr(fe, 'status', None) if fe is not None else None,
        'fe_cufe': (getattr(fe, 'cufe', None) or '').strip() if fe is not None else '',
        'fe_protocolo': (getattr(fe, 'pac_reference', None) or '').strip() if fe is not None else '',
        'fe_authorized_at': format_datetime_from_cfg(
            getattr(fe, 'authorized_at', None) or getattr(fe, 'accepted_at', None), cfg
        )
        if fe is not None
        else '',
        'fe_banner': banner,
        'origin_quotation_id': getattr(invoice, 'origin_quotation_id', None),
        'lines': lines or [],
        'cfg': cfg,
        'paper_size': str((cfg or {}).get('paper_size') or 'letter').lower(),
    }


def _customer_dict(invoice: Invoice) -> dict[str, str]:
    contact = get_invoice_fiscal_contact(invoice)
    if isinstance(contact, Contact):
        loc = ', '.join([x for x in [contact.fiscal_address, contact.province, contact.district] if x])
        return {
            'name': fiscal_display_name(contact),
            'tax_id': (contact.tax_id or '').strip(),
            'dv': (contact.dv or '').strip(),
            'address': loc,
            'phone': (contact.phone or contact.mobile or '').strip(),
            'email': (contact.email or '').strip(),
        }
    if isinstance(contact, TenantCrmContact):
        return {
            'name': (contact.legal_name or contact.name or '').strip(),
            'tax_id': (getattr(contact, 'tax_id', None) or '').strip(),
            'dv': (getattr(contact, 'tax_dv', None) or '').strip(),
            'address': '',
            'phone': (contact.phone or '').strip(),
            'email': (contact.email or '').strip(),
        }
    user = User.query.get(invoice.customer_id) if invoice.customer_id else None
    if user:
        return {
            'name': f'{user.first_name or ""} {user.last_name or ""}'.strip() or (user.email or 'Cliente'),
            'tax_id': '',
            'dv': '',
            'address': '',
            'phone': '',
            'email': (user.email or '').strip(),
        }
    return {'name': 'Cliente', 'tax_id': '', 'dv': '', 'address': '', 'phone': '', 'email': ''}


def _line_rows(invoice: Invoice) -> list[dict[str, Any]]:
    rows = []
    lines = InvoiceLine.query.filter_by(invoice_id=invoice.id).order_by(InvoiceLine.id.asc()).all()
    pids = [ln.product_id for ln in lines if ln.product_id]
    names = {}
    if pids:
        for s in Service.query.filter(Service.id.in_(pids), Service.organization_id == invoice.organization_id).all():
            names[s.id] = s.name or ''
    for ln in lines:
        raw = str(ln.description or '')
        is_note = raw.startswith('__NOTE__ ')
        desc = raw.replace('__NOTE__ ', '', 1) if is_note else raw
        pname = names.get(ln.product_id) or ''
        if pname and not is_note:
            desc = f'{pname} — {desc}' if desc and desc != pname else pname
        tax_amt = float(ln.total or 0) - float(ln.subtotal or 0)
        rows.append(
            {
                'description': desc.strip() or '—',
                'is_note': is_note,
                'quantity': float(ln.quantity or 0),
                'price_unit': float(ln.price_unit or 0),
                'tax_amount': tax_amt,
                'total': float(ln.total or 0),
            }
        )
    return rows


def render_invoice_pdf_bytes(invoice: Invoice, *, fe=None, org=None) -> bytes:
    cfg = _cfg_dict(invoice.organization_id)
    if fe is None and getattr(invoice, 'id', None):
        fe = find_latest_fe_for_invoice(invoice.id, invoice.organization_id)
    org = org or SaasOrganization.query.get(invoice.organization_id)
    ctx = build_invoice_visual_context(
        invoice,
        fe=fe,
        org=org,
        customer=_customer_dict(invoice),
        lines=_line_rows(invoice),
        cfg=cfg,
    )
    return render_invoice_pdf_from_context(ctx)


def render_invoice_pdf_from_context(ctx: dict[str, Any]) -> bytes:
    cfg = ctx.get('cfg') or {}
    paper = letter if str(ctx.get('paper_size') or 'letter').lower() == 'letter' else A4
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=paper,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.2 * cm,
        title=f"Factura {ctx.get('number') or ''}",
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle('InvSmall', parent=styles['Normal'], fontSize=8, leading=11, textColor=MUTED)
    body = ParagraphStyle('InvBody', parent=styles['Normal'], fontSize=9, leading=12, textColor=INK)
    title = ParagraphStyle('InvTitle', parent=styles['Normal'], fontSize=22, leading=26, textColor=NAVY, fontName='Helvetica-Bold')
    h_fe = ParagraphStyle('InvFe', parent=styles['Normal'], fontSize=11, leading=14, textColor=NAVY, fontName='Helvetica-Bold')
    warn = ParagraphStyle('InvWarn', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#92400e'))
    story: list = []

    logo_flow = None
    try:
        lp = _logo_path(int(ctx['organization_id']))
        if lp:
            logo_flow = Image(lp, width=2.6 * cm, height=1.6 * cm)
    except Exception:
        logo_flow = None

    left_bits = []
    if logo_flow:
        left_bits.append(logo_flow)
        left_bits.append(Spacer(1, 0.12 * cm))
    left_bits.append(Paragraph(f"<b>{_e(ctx['org_legal_name'])}</b>", body))
    if ctx.get('org_trade_name'):
        left_bits.append(Paragraph(_e(ctx['org_trade_name']), small))
    if ctx.get('org_tax_id'):
        left_bits.append(Paragraph(f"RUC: {_e(ctx['org_tax_id'])}", small))
    loc = ', '.join([x for x in [ctx.get('org_address'), ctx.get('org_city'), ctx.get('org_state'), ctx.get('org_country')] if x])
    if loc:
        left_bits.append(Paragraph(_e(loc), small))
    contact_l = ' · '.join([x for x in [ctx.get('org_phone'), ctx.get('org_email')] if x])
    if contact_l:
        left_bits.append(Paragraph(_e(contact_l), small))

    cufe = ctx.get('fe_cufe') or ''
    cufe_short = (cufe[:18] + '…') if len(cufe) > 22 else cufe
    right_bits = [
        Paragraph('FACTURA', title),
        Paragraph(f"N.º {_e(ctx.get('number') or '')}", body),
        Paragraph(f"Fecha: {_e(ctx.get('date_label') or '—')}", small),
    ]
    if ctx.get('due_label'):
        right_bits.append(Paragraph(f"Vencimiento: {_e(ctx['due_label'])}", small))
    right_bits.append(Paragraph(f"Estado: {_e(ctx.get('invoice_status') or '')}", small))
    if ctx.get('fe_status'):
        right_bits.append(Paragraph(f"Estado FE: {_e(ctx['fe_status'])}", small))
    if cufe_short and ctx.get('show_qr'):
        right_bits.append(Paragraph(f"CUFE: {_e(cufe_short)}", small))

    header = Table(
        [[left_bits, right_bits]],
        colWidths=[10.2 * cm, 7.4 * cm],
    )
    header.setStyle(
        TableStyle(
            [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 0.35 * cm))

    bill_bits = [Paragraph('<b>Facturado a</b>', body)]
    if ctx.get('customer_name'):
        bill_bits.append(Paragraph(_e(ctx['customer_name']), body))
    if ctx.get('customer_tax_id'):
        dv = f" DV {_e(ctx['customer_dv'])}" if ctx.get('customer_dv') else ''
        bill_bits.append(Paragraph(f"RUC / Doc.: {_e(ctx['customer_tax_id'])}{dv}", small))
    elif ctx.get('customer_dv'):
        bill_bits.append(Paragraph(f"DV: {_e(ctx['customer_dv'])}", small))
    for key, label in (('customer_address', ''), ('customer_phone', 'Tel. '), ('customer_email', '')):
        val = ctx.get(key)
        if val:
            bill_bits.append(Paragraph(_e(f'{label}{val}'), small))
    bill = Table([[bill_bits]], colWidths=[17.6 * cm])
    bill.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), BG),
                ('BOX', (0, 0), (-1, -1), 0.4, LINE),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(bill)
    story.append(Spacer(1, 0.4 * cm))

    data = [
        [
            Paragraph('<b>Descripción</b>', small),
            Paragraph('<b>Cantidad</b>', small),
            Paragraph('<b>Precio</b>', small),
            Paragraph('<b>Impuesto</b>', small),
            Paragraph('<b>Total</b>', small),
        ]
    ]
    for ln in ctx.get('lines') or []:
        if ln.get('is_note'):
            data.append(
                [
                    Paragraph(f"<i>{_e(ln.get('description'))}</i>", small),
                    Paragraph('—', small),
                    Paragraph('—', small),
                    Paragraph('—', small),
                    Paragraph('—', small),
                ]
            )
            continue
        tax_cell = _money(ln.get('tax_amount') or 0, cfg)
        data.append(
            [
                Paragraph(_e(ln.get('description') or '—'), small),
                Paragraph(_qty(ln.get('quantity') or 0, cfg), small),
                Paragraph(_money(ln.get('price_unit') or 0, cfg), small),
                Paragraph(_e(tax_cell), small),
                Paragraph(_money(ln.get('total') or 0, cfg), small),
            ]
        )
    if len(data) < 2:
        data.append(
            [
                Paragraph('<i>Sin líneas</i>', small),
                Paragraph('—', small),
                Paragraph('—', small),
                Paragraph('—', small),
                Paragraph('—', small),
            ]
        )
    tw = [7.4 * cm, 2.2 * cm, 2.6 * cm, 2.6 * cm, 2.8 * cm]
    table = Table(data, colWidths=tw, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.25, LINE),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.45 * cm))

    tot_rows = [
        [Paragraph('Subtotal', small), Paragraph(_money(ctx.get('subtotal') or 0, cfg), body)],
    ]
    if float(ctx.get('discount') or 0) > 0.004:
        tot_rows.append(
            [Paragraph('Descuentos', small), Paragraph(_money(ctx.get('discount') or 0, cfg), body)]
        )
    tot_rows.append(
        [Paragraph('Impuestos / ITBMS', small), Paragraph(_money(ctx.get('tax_total') or 0, cfg), body)]
    )
    tot_rows.append(
        [
            Paragraph('<b>TOTAL</b>', ParagraphStyle('T', parent=body, textColor=colors.white, fontName='Helvetica-Bold')),
            Paragraph(
                f"<b>{_e(_money(ctx.get('grand_total') or 0, cfg))}</b>",
                ParagraphStyle('T2', parent=body, textColor=colors.white, fontName='Helvetica-Bold'),
            ),
        ]
    )
    tot_rows.append([Paragraph('Pagado', small), Paragraph(_money(ctx.get('amount_paid') or 0, cfg), body)])
    tot_rows.append([Paragraph('Pendiente', small), Paragraph(_money(ctx.get('amount_due') or 0, cfg), body)])
    tot = Table(tot_rows, colWidths=[4.2 * cm, 4.0 * cm])
    total_idx = 2 if float(ctx.get('discount') or 0) <= 0.004 else 3
    tot.setStyle(
        TableStyle(
            [
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BACKGROUND', (0, total_idx), (-1, total_idx), TOTAL_BG),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('LINEBELOW', (0, 0), (-1, total_idx - 1), 0.3, LINE),
            ]
        )
    )
    wrap = Table([['', tot]], colWidths=[9.4 * cm, 8.2 * cm])
    wrap.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story.append(wrap)
    story.append(Spacer(1, 0.5 * cm))

    if ctx.get('show_qr') and ctx.get('fe_cufe'):
        qr_flow = _qr_image_flowable(ctx.get('qr_image_bytes'), ctx.get('qr_payload'))
        fe_left = [
            Paragraph('FACTURA ELECTRÓNICA', h_fe),
            Spacer(1, 0.12 * cm),
            Paragraph(f"CUFE: {_e(ctx['fe_cufe'])}", small),
        ]
        if ctx.get('fe_protocolo'):
            fe_left.append(Paragraph(f"Protocolo / autorización: {_e(ctx['fe_protocolo'])}", small))
        if ctx.get('fe_authorized_at'):
            fe_left.append(Paragraph(f"Fecha de autorización: {_e(ctx['fe_authorized_at'])}", small))
        qr_cell = [qr_flow] if qr_flow else [Paragraph('QR no disponible', small)]
        fe_tbl = Table([[fe_left, qr_cell]], colWidths=[12.8 * cm, 4.8 * cm])
        fe_tbl.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('BOX', (0, 0), (-1, -1), 0.6, NAVY),
                    ('BACKGROUND', (1, 0), (1, 0), colors.white),
                    ('LEFTPADDING', (0, 0), (0, 0), 10),
                    ('RIGHTPADDING', (1, 0), (1, 0), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (1, 0), (1, 0), 10),
                ]
            )
        )
        story.append(KeepTogether([fe_tbl]))
    else:
        banner = ctx.get('fe_banner') or ''
        if banner:
            story.append(
                Table(
                    [[Paragraph(_e(banner), warn)]],
                    colWidths=[17.6 * cm],
                )
            )

    doc.build(story)
    return buf.getvalue()


def invoice_pdf_attachment(invoice: Invoice, *, fe=None, org=None) -> dict[str, Any]:
    """Listo para adjuntar al correo del cliente (misma infraestructura de notificaciones)."""
    pdf = render_invoice_pdf_bytes(invoice, fe=fe, org=org)
    number = (invoice.number or f'INV-{invoice.id}').replace('/', '-')
    return {
        'filename': f'Factura-{number}.pdf',
        'content': pdf,
        'content_type': 'application/pdf',
    }


def load_invoice_for_visual(invoice_id: int, organization_id: int) -> Invoice | None:
    return Invoice.query.filter_by(id=int(invoice_id), organization_id=int(organization_id)).first()
