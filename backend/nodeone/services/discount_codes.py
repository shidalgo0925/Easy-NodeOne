"""Generación de códigos de descuento únicos (extraído de app.py)."""

import random
import string
import time


def generate_discount_code(prefix='DSC', length=8, custom_part=None):
    """
    Genera un código de descuento único automáticamente.

    Args:
        prefix: Prefijo del código (ej: "DSC", "EVT", "PROMO")
        length: Longitud de la parte aleatoria
        custom_part: Parte personalizada opcional (se inserta entre prefijo y aleatorio)

    Returns:
        str: Código único generado
    """
    import app as M

    max_attempts = 100
    attempt = 0

    while attempt < max_attempts:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

        if custom_part:
            code = f'{prefix}-{custom_part}-{random_part}'
        else:
            code = f'{prefix}-{random_part}'

        if not M.DiscountCode.query.filter_by(code=code).first():
            return code

        attempt += 1

    timestamp = str(int(time.time()))[-6:]
    code = f'{prefix}-{timestamp}'

    if M.DiscountCode.query.filter_by(code=code).first():
        code = f'{prefix}-{timestamp}-{random.randint(1000, 9999)}'

    return code
