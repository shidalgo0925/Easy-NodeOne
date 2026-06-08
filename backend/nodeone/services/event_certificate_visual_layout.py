"""Layout visual (Fabric/Canva) equivalente al PDF institucional Relatic para eventos."""

from __future__ import annotations

from typing import Any

CANVAS_WIDTH = 1056
CANVAS_HEIGHT = 816


def _cx(width: int, block_w: int) -> int:
    return max(0, (CANVAS_WIDTH - block_w) // 2)


def _el_text(
    el_id: str,
    value: str,
    *,
    y: int,
    font_size: int = 14,
    font_family: str = 'Times New Roman',
    align: str = 'center',
    width: int = 900,
    x: int | None = None,
    color: str = '#4A4A4A',
    font_weight: str = 'normal',
    font_style: str = 'normal',
) -> dict[str, Any]:
    if x is None:
        x = _cx(width, width) if align == 'center' else 60
    return {
        'id': el_id,
        'type': 'text',
        'value': value,
        'x': x,
        'y': y,
        'width': width,
        'fontSize': font_size,
        'fontFamily': font_family,
        'align': align,
        'color': color,
        'fontWeight': font_weight,
        'fontStyle': font_style,
    }


def _el_var(
    el_id: str,
    name: str,
    *,
    y: int,
    font_size: int = 14,
    font_family: str = 'Times New Roman',
    align: str = 'center',
    width: int = 900,
    x: int | None = None,
    color: str = '#4A4A4A',
    font_weight: str = 'normal',
    prefix: str = '',
    suffix: str = '',
) -> dict[str, Any]:
    if x is None:
        x = _cx(width, width) if align == 'center' else 60
    return {
        'id': el_id,
        'type': 'variable',
        'name': name,
        'prefix': prefix,
        'suffix': suffix,
        'x': x,
        'y': y,
        'width': width,
        'fontSize': font_size,
        'fontFamily': font_family,
        'align': align,
        'color': color,
        'fontWeight': font_weight,
    }


def _el_image(el_id: str, src: str, x: int, y: int, width: int, height: int) -> dict[str, Any]:
    return {
        'id': el_id,
        'type': 'image',
        'src': src,
        'x': x,
        'y': y,
        'width': width,
        'height': height,
    }


def build_institutional_visual_layout(layout: dict[str, Any], *, event_id: int) -> dict[str, Any]:
    """
    Construye json_layout visual con la configuración institucional actual
    (mismos campos que render_institutional_pdf + relatic_event_certificate_layout.json).
    """
    primary = (layout.get('primary_color') or '#002B5C').strip()
    text_color = (layout.get('text_color') or '#4A4A4A').strip()
    secondary = (layout.get('secondary_color') or '#F2B705').strip()

    header = (layout.get('header_text') or '').strip().upper()
    convenio = (layout.get('convenio_text') or '').strip()
    closing = (
        layout.get('closing_text')
        or 'En mérito a lo expuesto, y con el fin de acreditar su formación, se expide el presente diploma.'
    ).strip()
    logo_l = (layout.get('logo_left_url') or '').strip()
    logo_r = (layout.get('logo_right_url') or '').strip()
    seal = (layout.get('seal_url') or '').strip()

    sig_l_name = (layout.get('signatory_left_name') or '').strip()
    sig_l_role = (layout.get('signatory_left_role') or '').strip()
    sig_l_org = (layout.get('signatory_left_org') or '').strip()
    sig_r_name = (layout.get('signatory_right_name') or '').strip()
    sig_r_role = (layout.get('signatory_right_role') or '').strip()
    sig_r_org = (layout.get('signatory_right_org') or '').strip()

    elements: list[dict[str, Any]] = [
        {
            'id': 'border_outer',
            'type': 'border',
            'x': 28,
            'y': 20,
            'width': CANVAS_WIDTH - 56,
            'height': CANVAS_HEIGHT - 40,
            'color': secondary,
            'lineWidth': 3,
        },
        {
            'id': 'border_inner',
            'type': 'border',
            'x': 38,
            'y': 30,
            'width': CANVAS_WIDTH - 76,
            'height': CANVAS_HEIGHT - 60,
            'color': primary,
            'lineWidth': 2,
        },
    ]

    if logo_l:
        elements.append(_el_image('logo_left', logo_l, 48, 36, 120, 64))
    if logo_r:
        elements.append(_el_image('logo_right', logo_r, CANVAS_WIDTH - 168, 36, 120, 64))

    if header:
        elements.append(
            _el_text('header', header, y=118, font_size=17, color=primary, font_weight='bold', width=920)
        )
    if convenio:
        elements.append(
            _el_text(
                'convenio',
                convenio,
                y=158,
                font_size=13,
                color=text_color,
                font_style='italic',
                width=820,
            )
        )

    elements.extend(
        [
            _el_text('otorgan', 'Otorgan a', y=198, font_size=22, color=text_color, width=400),
            _el_var(
                'var_participant_name',
                'participant_name',
                y=232,
                font_size=34,
                color=primary,
                font_weight='bold',
                width=920,
            ),
            _el_var(
                'var_document_id',
                'document_id',
                y=288,
                font_size=16,
                color=text_color,
                prefix='ID: ',
                width=500,
            ),
            _el_var('var_body_text', 'body_text', y=322, font_size=18, color=text_color, width=880),
            _el_var(
                'var_program_name',
                'program_name',
                y=358,
                font_size=24,
                color=primary,
                font_weight='bold',
                width=920,
            ),
            _el_var('var_event_dates', 'event_dates', y=402, font_size=14, color=text_color, width=800),
            _el_var('var_hours_line', 'hours_line', y=428, font_size=14, color=text_color, width=700),
            _el_text('closing', closing, y=468, font_size=14, color=text_color, width=860),
            _el_var(
                'var_issue_legal',
                'issue_date_legal',
                y=548,
                font_size=13,
                color=text_color,
                width=900,
            ),
        ]
    )

    if seal:
        elements.append(_el_image('seal', seal, (CANVAS_WIDTH - 80) // 2, 600, 80, 80))

    # Firmas izquierda
    elements.extend(
        [
            _el_text('sig_l_line', '_________________________', y=668, font_size=12, align='left', width=320, x=72),
            _el_text('sig_l_name', sig_l_name, y=688, font_size=11, align='left', width=320, x=72, color='#222222'),
            _el_text('sig_l_role', sig_l_role, y=706, font_size=10, align='left', width=320, x=72),
            _el_text('sig_l_org', sig_l_org, y=722, font_size=9, align='left', width=320, x=72),
            _el_text('sig_r_line', '_________________________', y=668, font_size=12, align='left', width=320, x=664),
            _el_text('sig_r_name', sig_r_name, y=688, font_size=11, align='left', width=320, x=664, color='#222222'),
            _el_text('sig_r_role', sig_r_role, y=706, font_size=10, align='left', width=320, x=664),
            _el_text('sig_r_org', sig_r_org, y=722, font_size=9, align='left', width=320, x=664),
        ]
    )

    elements.extend(
        [
            {'id': 'qr', 'type': 'qr', 'variable': 'verification_url', 'x': 930, 'y': 640, 'size': 88},
            _el_text('qr_hint', 'Escanea para verificar', y=738, font_size=9, align='left', width=200, x=900),
            _el_var(
                'var_code',
                'certificate_code',
                y=754,
                font_size=9,
                align='left',
                width=220,
                x=900,
                prefix='Código: ',
                font_weight='bold',
            ),
            _el_var(
                'var_verify_url',
                'verification_url',
                y=770,
                font_size=8,
                align='left',
                width=220,
                x=900,
            ),
        ]
    )

    return {
        'canvas': {'width': CANVAS_WIDTH, 'height': CANVAS_HEIGHT},
        'elements': elements,
        'meta': {
            'event_id': int(event_id),
            'layout_kind': 'institutional_visual',
            'primary_color': primary,
            'secondary_color': secondary,
        },
    }
