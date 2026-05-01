from __future__ import annotations

import io

try:
    from PIL import Image as PILImage

    _LANCZOS = getattr(getattr(PILImage, 'Resampling', PILImage), 'LANCZOS', PILImage.LANCZOS)
except Exception:
    _LANCZOS = 1


def _error_correction(code: str):
    from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q

    return {
        'L': ERROR_CORRECT_L,
        'M': ERROR_CORRECT_M,
        'Q': ERROR_CORRECT_Q,
        'H': ERROR_CORRECT_H,
    }.get(code, ERROR_CORRECT_M)


def _resolve_style(style: dict | None) -> dict:
    from nodeone.modules.qr_generator.schemas import DEFAULT_BG, DEFAULT_BORDER_MODULES, DEFAULT_FILL
    from nodeone.modules.qr_generator.utils import normalize_hex_color, parse_border

    st = style or {}
    fill = normalize_hex_color(st.get('fill'), DEFAULT_FILL)
    bg = normalize_hex_color(st.get('bg'), DEFAULT_BG)
    return {
        'fill': fill,
        'bg': bg,
        'transparent': bool(st.get('transparent')),
        'border': parse_border(st.get('border')),
        'logo_bytes': st.get('logo_bytes'),
    }


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _apply_transparent_bg_rgba(img_rgba: PILImage.Image, rgb_bg: tuple[int, int, int]) -> PILImage.Image:
    r0, g0, b0 = rgb_bg
    data = list(img_rgba.getdata())
    out = []
    for px in data:
        r, g, b, a = px
        if r == r0 and g == g0 and b == b0:
            out.append((255, 255, 255, 0))
        else:
            out.append((r, g, b, a if a is not None else 255))
    img_rgba.putdata(out)
    return img_rgba


def _overlay_logo(qr_rgba: PILImage.Image, logo_bytes: bytes, max_fraction: float = 0.22) -> PILImage.Image:
    logo = PILImage.open(io.BytesIO(logo_bytes)).convert('RGBA')
    w, h = qr_rgba.size
    side = max(8, int(min(w, h) * max_fraction))
    logo.thumbnail((side, side), _LANCZOS)
    lw, lh = logo.size
    pos = ((w - lw) // 2, (h - lh) // 2)
    dest = qr_rgba.copy()
    dest.paste(logo, pos, logo)
    return dest


def generate_png_bytes(content: str, size: int, error_level: str, style: dict | None = None) -> bytes:
    import qrcode

    st = _resolve_style(style)
    fill, bg = st['fill'], st['bg']
    border = st['border']
    transparent = st['transparent']
    logo_raw = st.get('logo_bytes')
    logo_bytes = bytes(logo_raw) if isinstance(logo_raw, (bytes, bytearray)) else None

    back_for_qr = '#ffffff' if transparent else bg
    qr = qrcode.QRCode(
        version=None,
        error_correction=_error_correction(error_level),
        box_size=10,
        border=border,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back_for_qr).convert('RGB')
    img = img.resize((int(size), int(size)), _LANCZOS)

    if transparent:
        img = img.convert('RGBA')
        img = _apply_transparent_bg_rgba(img, _hex_to_rgb(back_for_qr))
        if logo_bytes:
            img = _overlay_logo(img, logo_bytes)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    if logo_bytes:
        img = img.convert('RGBA')
        img = _overlay_logo(img, logo_bytes)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def generate_svg_bytes(content: str, size: int, error_level: str, style: dict | None = None) -> bytes:
    import segno

    st = _resolve_style(style)
    fill, bg = st['fill'], st['bg']
    transparent = st['transparent']
    border = st['border']
    err = error_level.lower()

    scale = max(1, min(24, int(size) // 24))
    out = io.BytesIO()
    light = '#ffffff00' if transparent else bg
    try:
        qr = segno.make(content, error=err, boost_error=False)
        qr.save(out, kind='svg', scale=scale, border=border, dark=fill, light=light)
    except Exception:
        out = io.BytesIO()
        qr = segno.make(content, error=err, boost_error=False)
        qr.save(out, kind='svg', scale=scale, border=border, dark=fill, light=bg)

    return out.getvalue()


def generate_pdf_bytes(content: str, size: int, error_level: str, style: dict | None = None) -> bytes:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    png = generate_png_bytes(content, int(size), error_level, style)
    page = float(int(size) + 72)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page, page))
    img_buf = io.BytesIO(png)
    c.drawImage(ImageReader(img_buf), 36, 36, width=float(size), height=float(size), mask='auto')
    c.showPage()
    c.save()
    return buf.getvalue()


def generate_file(
    content: str,
    fmt: str,
    size: int,
    error_level: str,
    style: dict | None = None,
) -> tuple[bytes, str, str]:
    fmt = (fmt or 'png').lower()
    if fmt == 'png':
        data = generate_png_bytes(content, size, error_level, style)
        return data, 'image/png', 'qr.png'
    if fmt == 'svg':
        data = generate_svg_bytes(content, size, error_level, style)
        return data, 'image/svg+xml; charset=utf-8', 'qr.svg'
    if fmt == 'pdf':
        data = generate_pdf_bytes(content, size, error_level, style)
        return data, 'application/pdf', 'qr.pdf'
    raise ValueError('format')
