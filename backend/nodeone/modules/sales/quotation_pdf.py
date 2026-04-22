"""PDF simple para adjuntar a correos de cotización (ReportLab)."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.catalog import Service
from nodeone.modules.sales.models import QuotationLine


def _e(s) -> str:
    return escape(str(s) if s is not None else '', {'"': '&quot;', "'": '&apos;'})


def _product_names(organization_id: int, lines: list) -> dict:
    ids = list({ln.product_id for ln in lines if getattr(ln, 'product_id', None)})
    if not ids:
        return {}
    rows = Service.query.filter(Service.id.in_(ids), Service.organization_id == organization_id).all()
    return {s.id: (s.name or '') for s in rows}


def render_quotation_pdf_bytes(quotation, customer, org_profile) -> bytes:
    """Genera PDF en memoria. Falla con ImportError si falta reportlab."""
    lines = (
        QuotationLine.query.filter_by(quotation_id=quotation.id).order_by(QuotationLine.id.asc()).all()
    )
    pnames = _product_names(quotation.organization_id, lines)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#444444'),
    )
    story = []

    if isinstance(org_profile, dict):
        org_name = (org_profile.get('legal_name') or org_profile.get('name') or '').strip()
        org_tax_id = (org_profile.get('tax_id') or '').strip()
        org_address = (org_profile.get('fiscal_address') or '').strip()
        org_city = (org_profile.get('fiscal_city') or '').strip()
        org_state = (org_profile.get('fiscal_state') or '').strip()
        org_country = (org_profile.get('fiscal_country') or '').strip()
        org_phone = (org_profile.get('fiscal_phone') or '').strip()
        org_email = (org_profile.get('fiscal_email') or '').strip()
    else:
        org_name = str(org_profile or '').strip()
        org_tax_id = ''
        org_address = ''
        org_city = ''
        org_state = ''
        org_country = ''
        org_phone = ''
        org_email = ''

    on = _e(org_name or 'Organización')
    story.append(Paragraph(f'<b>{on}</b>', styles['Normal']))
    if org_tax_id:
        story.append(Paragraph(f'RUC/NIT: {_e(org_tax_id)}', small))
    loc = ', '.join([x for x in [org_city, org_state, org_country] if x])
    if org_address:
        story.append(Paragraph(_e(org_address), small))
    if loc:
        story.append(Paragraph(_e(loc), small))
    if org_phone or org_email:
        story.append(Paragraph(_e(' · '.join([x for x in [org_phone, org_email] if x])), small))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(f'<b>Cotización {_e(quotation.number)}</b>', styles['Heading2']))
    story.append(Spacer(1, 0.35 * cm))

    cn = _e(
        (
            f"{getattr(customer, 'first_name', '') or ''} {getattr(customer, 'last_name', '') or ''}"
        ).strip()
        or 'Cliente'
    )
    ce = _e(getattr(customer, 'email', '') or '')
    story.append(Paragraph(f'Cliente: <b>{cn}</b>', styles['Normal']))
    if ce:
        story.append(Paragraph(ce, small))
    story.append(Spacer(1, 0.4 * cm))

    data = [
        [
            Paragraph('<b>Descripción</b>', small),
            Paragraph('<b>Cant.</b>', small),
            Paragraph('<b>P. unit.</b>', small),
            Paragraph('<b>Importe</b>', small),
        ]
    ]
    for ln in lines:
        raw = str(ln.description or '')
        is_note = raw.startswith('__NOTE__ ')
        desc = raw.replace('__NOTE__ ', '', 1) if is_note else raw
        label = (pnames.get(ln.product_id) or '').strip()
        if label and not is_note:
            desc = f'{label} — {desc}'
        if is_note:
            data.append(
                [
                    Paragraph(f'<i>{_e(desc)}</i>', small),
                    Paragraph('—', small),
                    Paragraph('—', small),
                    Paragraph('—', small),
                ]
            )
            continue
        qty = float(ln.quantity or 0)
        pu = float(ln.price_unit or 0)
        tot = float(ln.total or 0)
        data.append(
            [
                Paragraph(_e(desc.strip() or '—'), small),
                Paragraph(_e(f'{qty:.2f}'), small),
                Paragraph(_e(f'{pu:.2f}'), small),
                Paragraph(_e(f'{tot:.2f}'), small),
            ]
        )

    tw = [10 * cm, 2.2 * cm, 2.5 * cm, 2.8 * cm]
    if len(data) < 2:
        data.append(
            [
                Paragraph('<i>Sin líneas</i>', small),
                Paragraph('—', small),
                Paragraph('—', small),
                Paragraph('—', small),
            ]
        )

    t = Table(data, colWidths=tw, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3dcc')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    sub = float(quotation.total or 0)
    tax = float(quotation.tax_total or 0)
    grand = float(quotation.grand_total or 0)
    story.append(Paragraph(f'Subtotal: <b>B/. {sub:.2f}</b>', styles['Normal']))
    story.append(Paragraph(f'Impuestos: <b>B/. {tax:.2f}</b>', styles['Normal']))
    story.append(Paragraph(f'<b>Total: B/. {grand:.2f}</b>', styles['Normal']))

    doc.build(story)
    return buf.getvalue()
