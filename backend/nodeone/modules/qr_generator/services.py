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
    }[code]


def generate_png_bytes(content: str, size: int, error_level: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(version=None, error_correction=_error_correction(error_level), box_size=10, border=2)
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white').convert('RGB')
    img = img.resize((int(size), int(size)), _LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def generate_svg_bytes(content: str, size: int, error_level: str) -> bytes:
    import segno

    err = error_level.lower()
    qr = segno.make(content, error=err, boost_error=False)
    scale = max(1, min(24, int(size) // 24))
    out = io.BytesIO()
    qr.save(out, kind='svg', scale=scale, border=4)
    raw = out.getvalue()
    return raw


def generate_pdf_bytes(content: str, size: int, error_level: str) -> bytes:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    png = generate_png_bytes(content, int(size), error_level)
    page = float(int(size) + 72)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page, page))
    img_buf = io.BytesIO(png)
    c.drawImage(ImageReader(img_buf), 36, 36, width=float(size), height=float(size), mask='auto')
    c.showPage()
    c.save()
    return buf.getvalue()


def generate_file(content: str, fmt: str, size: int, error_level: str) -> tuple[bytes, str, str]:
    fmt = (fmt or 'png').lower()
    if fmt == 'png':
        data = generate_png_bytes(content, size, error_level)
        return data, 'image/png', 'qr.png'
    if fmt == 'svg':
        data = generate_svg_bytes(content, size, error_level)
        return data, 'image/svg+xml; charset=utf-8', 'qr.svg'
    if fmt == 'pdf':
        data = generate_pdf_bytes(content, size, error_level)
        return data, 'application/pdf', 'qr.pdf'
    raise ValueError('format')
