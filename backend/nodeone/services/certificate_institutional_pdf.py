"""Renderer PDF institucional único para certificados (eventos EN1 y fallback membresía).

Un solo motor visual: QR, layout, tipografías y export PDF ReportLab landscape.
"""

from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# --- Colores y página (constantes compartidas) ---

COLOR_PRIMARY = '#002B5C'
COLOR_SECONDARY = '#F2B705'
COLOR_ACCENT = '#005AA7'
COLOR_TEXT = '#4A4A4A'
COLOR_TITLE = '#222222'

PX_TO_PT = 0.75
MARGIN_TOP_PT = 35 * PX_TO_PT
MARGIN_BOTTOM_PT = 35 * PX_TO_PT
MARGIN_LEFT_PT = 45 * PX_TO_PT
MARGIN_RIGHT_PT = 45 * PX_TO_PT

_ACADEMIC_TYPES = frozenset({'diplomado', 'curso', 'taller', 'seminario'})

_SPANISH_MONTHS = (
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'septiembre',
    'octubre',
    'noviembre',
    'diciembre',
)

_SPANISH_UNITS = (
    'cero',
    'uno',
    'dos',
    'tres',
    'cuatro',
    'cinco',
    'seis',
    'siete',
    'ocho',
    'nueve',
    'diez',
    'once',
    'doce',
    'trece',
    'catorce',
    'quince',
    'dieciséis',
    'diecisiete',
    'dieciocho',
    'diecinueve',
    'veinte',
    'veintiuno',
    'veintidós',
    'veintitrés',
    'veinticuatro',
    'veinticinco',
    'veintiséis',
    'veintisiete',
    'veintiocho',
    'veintinueve',
    'treinta',
    'treinta y uno',
)


def qr_png_base64(verify_url: str) -> str | None:
    """QR PNG en base64 (única implementación)."""
    try:
        import qrcode

        buf = io.BytesIO()
        qrcode.make(verify_url).save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def hex_to_rgb(hex_color: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
    h = (hex_color or '').strip().lstrip('#')
    if len(h) != 6:
        return default
    try:
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)
    except ValueError:
        return default


def resolve_certificate_asset(url: str | None, app_root: str | None = None) -> str | None:
    """Resuelve /static/uploads/certificates/... a ruta absoluta en disco."""
    if not url:
        return None
    u = (url or '').strip()
    if u.startswith('file://'):
        p = u[7:]
        return p if os.path.isfile(p) else None
    if u.startswith('http://') or u.startswith('https://'):
        return None
    rel = u
    if '/static/' in u:
        rel = u.split('/static/', 1)[-1].split('?')[0].strip()
    elif u.startswith('/static/'):
        rel = u[len('/static/') :].split('?')[0].strip()
    elif u.startswith('static/'):
        rel = u[len('static/') :].split('?')[0].strip()

    roots: list[str] = []
    if app_root:
        roots.append(os.path.abspath(os.path.join(app_root, '..', 'static')))
    roots.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static')))

    for static_root in roots:
        path = os.path.abspath(os.path.join(static_root, rel.replace('/', os.sep)))
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext == '.svg':
                return None
            return path
    return None


def day_to_spanish_words(day: int) -> str:
    if 0 <= day < len(_SPANISH_UNITS):
        return _SPANISH_UNITS[day]
    return str(day)


def format_issue_date_legal(dt: datetime, city: str = 'Panamá') -> str:
    ciudad = (city or 'Panamá').strip()
    mes = _SPANISH_MONTHS[dt.month - 1] if 1 <= dt.month <= 12 else str(dt.month)
    dia = day_to_spanish_words(dt.day)
    return f'Dado en la ciudad de {ciudad} a los {dia} días del mes de {mes} del {dt.year}'


def format_event_date_range(start: datetime | None, end: datetime | None) -> str | None:
    if not start and not end:
        return None
    fmt = '%d/%m/%Y'

    def _f(d: datetime | None) -> str:
        return d.strftime(fmt) if d else '—'

    if start and end:
        return f'Realizado del {_f(start)} hasta el {_f(end)}'
    if start:
        return f'Realizado el {_f(start)}'
    return f'Realizado hasta el {_f(end)}'


def compute_academic_hours(
    start: datetime | None,
    end: datetime | None,
    configured: float | int | None,
) -> float | None:
    if configured is not None:
        try:
            h = float(configured)
            return h if h > 0 else None
        except (TypeError, ValueError):
            pass
    if start and end:
        delta = end - start
        hours = delta.total_seconds() / 3600.0
        if hours > 0:
            return round(hours, 1)
    return None


def body_text_for_type(*, participant_type: str, activity_type: str) -> str:
    pt = (participant_type or '').strip().lower()
    if pt == 'reviewer':
        return 'por su participación como revisor en:'
    at = (activity_type or '').strip()
    if at.lower() in _ACADEMIC_TYPES:
        label = at if at else 'Programa'
        return f'por haber culminado satisfactoriamente los requisitos del {label} académico en:'
    return 'por haber participado en el evento:'


@dataclass
class CertificateRenderContext:
    """Datos normalizados para el PDF institucional (eventos y membresía)."""

    participant_name: str
    document_id: str
    program_name: str
    certificate_code: str
    verify_url: str
    issued_at: datetime
    participant_type: str = 'external'
    event_start: datetime | None = None
    event_end: datetime | None = None
    header_text: str = ''
    convenio_text: str = ''
    activity_type: str = 'Diplomado'
    academic_hours: float | None = None
    issue_city: str = 'Panamá'
    closing_text: str = (
        'En mérito a lo expuesto, y con el fin de acreditar su formación, se expide el presente diploma.'
    )
    primary_color: str = COLOR_PRIMARY
    secondary_color: str = COLOR_SECONDARY
    text_color: str = COLOR_TEXT
    title_color: str = COLOR_TITLE
    logo_left_path: str | None = None
    logo_right_path: str | None = None
    seal_path: str | None = None
    signatory_left_name: str = ''
    signatory_left_role: str = ''
    signatory_left_org: str = ''
    signatory_left_image: str | None = None
    signatory_right_name: str = ''
    signatory_right_role: str = ''
    signatory_right_org: str = ''
    signatory_right_image: str | None = None
    qr_base64: str | None = None
    app_root: str | None = None
    membership_type: str = ''
    membership_period: str = ''


def _load_org_layout_defaults(org_id: int) -> dict[str, Any]:
    """Carga JSON de layout por org; Relatic org 1 usa defaults del repo."""
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'relatic_event_certificate_layout.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', f'event_certificate_layout_org_{org_id}.json'),
    ]
    for path in candidates:
        abs_p = os.path.abspath(path)
        if os.path.isfile(abs_p):
            try:
                with open(abs_p, encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
    return {}


def _parse_event_layout_override(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    s = raw.strip()
    if not s.startswith('{'):
        return {}
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _merge_layout(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if v is not None and v != '':
            out[k] = v
    return out


def _resolve_asset_field(layout: dict[str, Any], key: str, app_root: str | None) -> str | None:
    return resolve_certificate_asset(layout.get(key), app_root)


def layout_from_certificate_event(cert_event, app_root: str | None = None) -> dict[str, Any]:
    """Mapea CertificateEvent (membresía) a dict de layout."""
    return {
        'header_text': getattr(cert_event, 'institution', '') or '',
        'convenio_text': getattr(cert_event, 'convenio', '') or '',
        'activity_type': 'Diplomado',
        'academic_hours': getattr(cert_event, 'duration_hours', None),
        'issue_city': 'Panamá',
        'logo_left_url': getattr(cert_event, 'logo_left_url', '') or '',
        'logo_right_url': getattr(cert_event, 'logo_right_url', '') or '',
        'seal_url': getattr(cert_event, 'seal_url', '') or '',
        'signatory_left_name': getattr(cert_event, 'rector_name', '') or '',
        'signatory_left_role': 'Rector',
        'signatory_left_org': getattr(cert_event, 'institution', '') or '',
        'signatory_right_name': getattr(cert_event, 'academic_director_name', '') or '',
        'signatory_right_role': 'Directora Académica',
        'signatory_right_org': getattr(cert_event, 'partner_organization', '') or '',
        'primary_color': COLOR_PRIMARY,
        'secondary_color': COLOR_SECONDARY,
    }


def build_context_from_event_participant(
    *,
    event,
    participant,
    certificate_code: str,
    verify_url: str,
    issued_at: datetime | None = None,
    app_root: str | None = None,
    org_id: int | None = None,
) -> CertificateRenderContext:
    """Adaptador Event + EventParticipant → contexto de render."""
    oid = int(org_id or 1)
    base = _load_org_layout_defaults(oid)
    override = _parse_event_layout_override(getattr(event, 'certificate_template', None))
    layout = _merge_layout(base, override)

    if getattr(event, 'university', None) and not layout.get('header_text'):
        uni = (event.university or '').strip()
        layout['header_text'] = uni

    display_name = (
        (getattr(participant, 'full_name', None) or '').strip()
        or ' '.join(
            x
            for x in (
                getattr(participant, 'first_name', None),
                getattr(participant, 'middle_name', None),
                getattr(participant, 'last_name', None),
                getattr(participant, 'second_last_name', None),
            )
            if x
        ).strip()
    )
    doc = (getattr(participant, 'document_id', None) or '').strip() or 'No registrado'
    issued = issued_at or datetime.utcnow()
    start = getattr(event, 'start_date', None)
    end = getattr(event, 'end_date', None)
    hours = compute_academic_hours(start, end, layout.get('academic_hours'))

    return CertificateRenderContext(
        participant_name=display_name or '—',
        document_id=doc,
        program_name=(getattr(event, 'title', None) or 'Evento').strip(),
        certificate_code=certificate_code,
        verify_url=verify_url,
        issued_at=issued,
        participant_type=(getattr(participant, 'participant_type', None) or 'external'),
        event_start=start,
        event_end=end,
        header_text=(layout.get('header_text') or '').strip(),
        convenio_text=(layout.get('convenio_text') or '').strip(),
        activity_type=(layout.get('activity_type') or 'Diplomado').strip(),
        academic_hours=hours,
        issue_city=(layout.get('issue_city') or 'Panamá').strip(),
        closing_text=(
            layout.get('closing_text')
            or 'En mérito a lo expuesto, y con el fin de acreditar su formación, se expide el presente diploma.'
        ),
        primary_color=layout.get('primary_color') or COLOR_PRIMARY,
        secondary_color=layout.get('secondary_color') or COLOR_SECONDARY,
        text_color=layout.get('text_color') or COLOR_TEXT,
        title_color=layout.get('title_color') or COLOR_TITLE,
        logo_left_path=_resolve_asset_field(layout, 'logo_left_url', app_root),
        logo_right_path=_resolve_asset_field(layout, 'logo_right_url', app_root),
        seal_path=_resolve_asset_field(layout, 'seal_url', app_root),
        signatory_left_name=(layout.get('signatory_left_name') or '').strip(),
        signatory_left_role=(layout.get('signatory_left_role') or '').strip(),
        signatory_left_org=(layout.get('signatory_left_org') or '').strip(),
        signatory_left_image=_resolve_asset_field(layout, 'signatory_left_image', app_root),
        signatory_right_name=(layout.get('signatory_right_name') or '').strip(),
        signatory_right_role=(layout.get('signatory_right_role') or '').strip(),
        signatory_right_org=(layout.get('signatory_right_org') or '').strip(),
        signatory_right_image=_resolve_asset_field(layout, 'signatory_right_image', app_root),
        qr_base64=qr_png_base64(verify_url),
        app_root=app_root,
    )


def build_context_from_membership(
    *,
    cert_event,
    full_name: str,
    program_name: str,
    certificate_code: str,
    verify_url: str,
    issued_at: datetime | None = None,
    app_root: str | None = None,
    membership_type: str = '',
    membership_start: str = '',
    membership_end: str = '',
    document_id: str = 'No registrado',
) -> CertificateRenderContext:
    """Adaptador CertificateEvent + usuario membresía → mismo contexto."""
    layout = layout_from_certificate_event(cert_event, app_root)
    issued = issued_at or datetime.utcnow()
    start = getattr(cert_event, 'start_date', None)
    end = getattr(cert_event, 'end_date', None)
    hours = compute_academic_hours(start, end, layout.get('academic_hours'))

    period = ''
    if membership_start or membership_end:
        period = f'{membership_start} – {membership_end}'.strip(' –')

    return CertificateRenderContext(
        participant_name=full_name or '—',
        document_id=document_id,
        program_name=program_name or getattr(cert_event, 'name', 'Certificado'),
        certificate_code=certificate_code,
        verify_url=verify_url,
        issued_at=issued,
        participant_type='external',
        event_start=start,
        event_end=end,
        header_text=(layout.get('header_text') or '').strip(),
        convenio_text=(layout.get('convenio_text') or '').strip(),
        activity_type=(layout.get('activity_type') or 'Diplomado').strip(),
        academic_hours=hours,
        issue_city=(layout.get('issue_city') or 'Panamá').strip(),
        primary_color=layout.get('primary_color') or COLOR_PRIMARY,
        secondary_color=layout.get('secondary_color') or COLOR_SECONDARY,
        logo_left_path=_resolve_asset_field(layout, 'logo_left_url', app_root),
        logo_right_path=_resolve_asset_field(layout, 'logo_right_url', app_root),
        seal_path=_resolve_asset_field(layout, 'seal_url', app_root),
        signatory_left_name=(layout.get('signatory_left_name') or '').strip(),
        signatory_left_role=(layout.get('signatory_left_role') or '').strip(),
        signatory_left_org=(layout.get('signatory_left_org') or '').strip(),
        signatory_left_image=None,
        signatory_right_name=(layout.get('signatory_right_name') or '').strip(),
        signatory_right_role=(layout.get('signatory_right_role') or '').strip(),
        signatory_right_org=(layout.get('signatory_right_org') or '').strip(),
        signatory_right_image=None,
        qr_base64=qr_png_base64(verify_url),
        app_root=app_root,
        membership_type=membership_type or '',
        membership_period=period,
    )


def _wrap_lines(text: str, font_name: str, font_size: float, max_width: float, canvas) -> list[str]:
    words = (text or '').split()
    if not words:
        return ['']
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f'{current} {word}'
        if canvas.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_centered_block(
    canvas,
    lines: list[str],
    center_x: float,
    y_top: float,
    *,
    font_name: str,
    font_size: float,
    color: tuple[float, float, float],
    line_leading: float | None = None,
) -> float:
    leading = line_leading or font_size * 1.25
    y = y_top
    canvas.setFont(font_name, font_size)
    canvas.setFillColorRGB(*color)
    for line in lines:
        canvas.drawCentredString(center_x, y, line)
        y -= leading
    return y


def _draw_image_fit(canvas, path: str | None, x: float, y: float, w: float, h: float) -> None:
    if not path or not os.path.isfile(path):
        return
    try:
        from reportlab.lib.utils import ImageReader

        canvas.drawImage(ImageReader(path), x, y, width=w, height=h, preserveAspectRatio=True, anchor='c')
    except Exception:
        pass


def render_institutional_pdf(ctx: CertificateRenderContext) -> bytes:
    """Genera PDF landscape Letter con layout institucional Relatic."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.pdfgen import canvas

    page_size = landscape(letter)
    w, h = page_size
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page_size)
    c.setTitle('Certificado')

    primary = hex_to_rgb(ctx.primary_color, (0, 43 / 255, 92 / 255))
    secondary = hex_to_rgb(ctx.secondary_color, (242 / 255, 183 / 255, 5 / 255))
    accent = hex_to_rgb(COLOR_ACCENT, (0, 90 / 255, 167 / 255))
    text_rgb = hex_to_rgb(ctx.text_color, (74 / 255, 74 / 255, 74 / 255))
    title_rgb = hex_to_rgb(ctx.title_color, (34 / 255, 34 / 255, 34 / 255))

    inner_l = MARGIN_LEFT_PT
    inner_r = w - MARGIN_RIGHT_PT
    inner_t = h - MARGIN_TOP_PT
    inner_b = MARGIN_BOTTOM_PT
    cx = w / 2
    content_w = inner_r - inner_l

    # Fondo y bordes decorativos
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColorRGB(*secondary)
    c.setLineWidth(2.5)
    c.rect(inner_l - 8, inner_b - 8, content_w + 16, inner_t - inner_b + 16, fill=0, stroke=1)
    c.setStrokeColorRGB(*primary)
    c.setLineWidth(1.2)
    c.rect(inner_l - 4, inner_b - 4, content_w + 8, inner_t - inner_b + 8, fill=0, stroke=1)

    # Logos superiores
    logo_w, logo_h = 90, 48
    _draw_image_fit(c, ctx.logo_left_path, inner_l, inner_t - logo_h - 4, logo_w, logo_h)
    _draw_image_fit(c, ctx.logo_right_path, inner_r - logo_w, inner_t - logo_h - 4, logo_w, logo_h)

    y = inner_t - logo_h - 18

    # Encabezado institucional
    if ctx.header_text:
        header_lines = _wrap_lines(ctx.header_text.upper(), 'Times-Bold', 13, content_w - 40, c)
        y = _draw_centered_block(c, header_lines, cx, y, font_name='Times-Bold', font_size=13, color=primary, line_leading=15)

    y -= 6
    if ctx.convenio_text:
        conv_lines = _wrap_lines(ctx.convenio_text, 'Times-Italic', 10, content_w - 60, c)
        y = _draw_centered_block(c, conv_lines, cx, y, font_name='Times-Italic', font_size=10, color=text_rgb, line_leading=12)

    y -= 14
    y = _draw_centered_block(c, ['Otorgan a'], cx, y, font_name='Times-Roman', font_size=17, color=text_rgb)

    y -= 6
    name_upper = (ctx.participant_name or '—').upper()
    name_lines = _wrap_lines(name_upper, 'Times-Bold', 28, content_w - 50, c)
    y = _draw_centered_block(c, name_lines, cx, y, font_name='Times-Bold', font_size=28, color=primary, line_leading=32)

    y -= 4
    y = _draw_centered_block(
        c,
        [f'ID: {ctx.document_id}'],
        cx,
        y,
        font_name='Helvetica',
        font_size=14,
        color=text_rgb,
    )

    y -= 10
    body = body_text_for_type(participant_type=ctx.participant_type, activity_type=ctx.activity_type)
    body_lines = _wrap_lines(body, 'Times-Roman', 15, content_w - 40, c)
    y = _draw_centered_block(c, body_lines, cx, y, font_name='Times-Roman', font_size=15, color=text_rgb, line_leading=17)

    y -= 6
    prog = f'"{(ctx.program_name or "—").upper()}"'
    prog_lines = _wrap_lines(prog, 'Times-Bold', 20, content_w - 50, c)
    y = _draw_centered_block(c, prog_lines, cx, y, font_name='Times-Bold', font_size=20, color=primary, line_leading=22)

    date_range = format_event_date_range(ctx.event_start, ctx.event_end)
    if date_range:
        y -= 8
        y = _draw_centered_block(c, [date_range], cx, y, font_name='Times-Roman', font_size=12, color=text_rgb)

    if ctx.academic_hours:
        y -= 6
        hrs = ctx.academic_hours
        hrs_txt = f'con una duración total de {hrs:g} horas' if hrs == int(hrs) else f'con una duración total de {hrs} horas'
        y = _draw_centered_block(c, [hrs_txt], cx, y, font_name='Times-Roman', font_size=12, color=text_rgb)

    if ctx.membership_type:
        y -= 6
        y = _draw_centered_block(
            c,
            [f'Membresía: {ctx.membership_type.upper()}'],
            cx,
            y,
            font_name='Times-Roman',
            font_size=11,
            color=text_rgb,
        )
    if ctx.membership_period:
        y -= 4
        y = _draw_centered_block(
            c,
            [f'Vigente: {ctx.membership_period}'],
            cx,
            y,
            font_name='Times-Roman',
            font_size=11,
            color=text_rgb,
        )

    y -= 10
    closing_lines = _wrap_lines(ctx.closing_text, 'Times-Roman', 12, content_w - 50, c)
    y = _draw_centered_block(c, closing_lines, cx, y, font_name='Times-Roman', font_size=12, color=text_rgb, line_leading=14)

    # Pie: fecha legal, firmas, sello
    footer_y = inner_b + 95
    issue_legal = format_issue_date_legal(ctx.issued_at, ctx.issue_city)
    issue_lines = _wrap_lines(issue_legal, 'Times-Roman', 11, content_w - 40, c)
    _draw_centered_block(c, issue_lines, cx, footer_y + 42, font_name='Times-Roman', font_size=11, color=text_rgb, line_leading=13)

    sig_w = (content_w - 80) / 2
    left_x = inner_l + 20
    right_x = inner_r - sig_w - 20
    seal_cx = cx

    def _signature_block(x: float, name: str, role: str, org: str, img: str | None) -> None:
        line_y = footer_y + 18
        c.setStrokeColorRGB(*accent)
        c.setLineWidth(0.8)
        c.line(x, line_y, x + sig_w - 10, line_y)
        if img:
            _draw_image_fit(c, img, x + sig_w / 2 - 35, line_y + 4, 70, 22)
        ty = line_y - 14
        c.setFont('Helvetica', 10)
        c.setFillColorRGB(*title_rgb)
        if name:
            c.drawCentredString(x + (sig_w - 10) / 2, ty, name[:48])
        ty -= 11
        c.setFont('Helvetica', 9)
        c.setFillColorRGB(*text_rgb)
        if role:
            c.drawCentredString(x + (sig_w - 10) / 2, ty, role[:52])
        ty -= 10
        if org:
            org_lines = _wrap_lines(org, 'Helvetica', 8, sig_w - 14, c)
            for ol in org_lines[:2]:
                c.drawCentredString(x + (sig_w - 10) / 2, ty, ol)
                ty -= 9

    _signature_block(left_x, ctx.signatory_left_name, ctx.signatory_left_role, ctx.signatory_left_org, ctx.signatory_left_image)
    _signature_block(right_x, ctx.signatory_right_name, ctx.signatory_right_role, ctx.signatory_right_org, ctx.signatory_right_image)

    # Sello central
    seal_size = 56
    if ctx.seal_path:
        _draw_image_fit(c, ctx.seal_path, seal_cx - seal_size / 2, footer_y - 8, seal_size, seal_size)
    else:
        c.setStrokeColorRGB(*secondary)
        c.setLineWidth(1.5)
        c.circle(seal_cx, footer_y + 20, seal_size / 2, fill=0, stroke=1)

    # QR + verificación (esquina inferior derecha)
    qr_size = 68
    qr_x = inner_r - qr_size - 4
    qr_y = inner_b + 6
    if ctx.qr_base64:
        try:
            from reportlab.lib.utils import ImageReader

            raw = base64.b64decode(ctx.qr_base64)
            c.drawImage(ImageReader(io.BytesIO(raw)), qr_x, qr_y + 28, width=qr_size, height=qr_size)
        except Exception:
            pass

    c.setFont('Helvetica', 8)
    c.setFillColorRGB(*text_rgb)
    c.drawString(qr_x - 2, qr_y + 20, 'Escanea para verificar')
    c.setFont('Helvetica-Bold', 8)
    code_short = ctx.certificate_code if len(ctx.certificate_code) <= 36 else ctx.certificate_code[:33] + '...'
    c.drawString(qr_x - 2, qr_y + 10, f'Código: {code_short}')
    c.setFont('Helvetica', 7)
    url = ctx.verify_url
    if len(url) > 52:
        url = url[:49] + '...'
    c.drawString(qr_x - 2, qr_y, url)

    c.save()
    buf.seek(0)
    return buf.getvalue()
