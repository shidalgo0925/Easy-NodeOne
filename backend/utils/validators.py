"""Validadores de entrada y utilidades de registro (extraído de app.py)."""

import re
import secrets


VALID_COUNTRIES = [
    'Argentina', 'Bolivia', 'Brasil', 'Chile', 'Colombia', 'Costa Rica',
    'Cuba', 'Ecuador', 'El Salvador', 'España', 'Guatemala', 'Honduras',
    'México', 'Nicaragua', 'Panamá', 'Paraguay', 'Perú', 'República Dominicana',
    'Uruguay', 'Venezuela', 'Estados Unidos', 'Canadá', 'Otro',
]


def validate_email_format(email):
    """
    Validación estricta de formato de email.
    Retorna (is_valid, error_message).
    """
    if not email or not isinstance(email, str):
        return False, "El email es obligatorio"

    email = email.strip().lower()

    if len(email) > 120:
        return False, "El email es demasiado largo (máximo 120 caracteres)"

    if len(email) < 5:
        return False, "El email es demasiado corto"

    email_regex = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
    if not re.match(email_regex, email):
        return False, "El formato del email no es válido"

    parts = email.split('@')
    if len(parts) != 2:
        return False, "El email debe tener un formato válido (usuario@dominio.com)"

    domain = parts[1]
    domain_parts = domain.split('.')
    if len(domain_parts) < 2:
        return False, "El dominio del email debe tener al menos una extensión (ej: .com, .org)"

    extension = domain_parts[-1]
    if len(extension) < 2 or not extension.isalpha():
        return False, "La extensión del dominio no es válida"

    blocked_domains = [
        'tempmail.com', 'mailinator.com', 'guerrillamail.com',
        '10minutemail.com', 'throwaway.email', 'temp-mail.org',
        'maildrop.cc', 'getnada.com', 'mohmal.com',
    ]

    if domain.lower() in blocked_domains:
        return False, "No se permiten direcciones de correo temporal"

    return True, None


def validate_country(country):
    """
    Validar que el país sea válido.
    Retorna (is_valid, error_message).
    """
    if not country or not isinstance(country, str):
        return False, "El país es obligatorio"

    country = country.strip()

    if country not in VALID_COUNTRIES:
        return False, f"El país '{country}' no es válido. Seleccione un país de la lista."

    return True, None


def validate_cedula_or_passport(cedula_or_passport, country=None):
    """
    Validar formato de cédula o pasaporte según el país.
    Retorna (is_valid, error_message).
    """
    if not cedula_or_passport or not isinstance(cedula_or_passport, str):
        return False, "La cédula o pasaporte es obligatorio"

    cedula_or_passport = cedula_or_passport.strip()

    if len(cedula_or_passport) < 4:
        return False, "La cédula o pasaporte es demasiado corta (mínimo 4 caracteres)"
    if len(cedula_or_passport) > 20:
        return False, "La cédula o pasaporte es demasiado larga (máximo 20 caracteres)"

    if country:
        country = country.strip()
        if country == 'Panamá':
            cleaned = re.sub(r'[-\s.]', '', cedula_or_passport)
            if not cleaned.isdigit():
                return False, "La cédula panameña debe contener solo números"
            if len(cleaned) < 7 or len(cleaned) > 10:
                return False, (
                    "La cédula panameña debe tener entre 7 y 10 dígitos numéricos "
                    "(ej.: 8-780-382, 8-123-4567 o 81234567; los guiones o espacios se ignoran)"
                )
        elif country == 'Colombia':
            cleaned = re.sub(r'[-\s.]', '', cedula_or_passport)
            if not cleaned.isdigit():
                return False, "La cédula colombiana debe contener solo números"
            if len(cleaned) < 7 or len(cleaned) > 10:
                return False, "La cédula colombiana debe tener entre 7 y 10 dígitos"
        elif country == 'Argentina':
            cleaned = re.sub(r'[-\s.]', '', cedula_or_passport)
            if not cleaned.isdigit():
                return False, "El DNI argentino debe contener solo números"
            if len(cleaned) < 7 or len(cleaned) > 8:
                return False, "El DNI argentino debe tener 7 u 8 dígitos"
        elif country == 'México':
            if not re.match(r'^[A-Z0-9]{10,18}$', cedula_or_passport.upper()):
                return False, "El formato de identificación mexicana no es válido (CURP o RFC)"

        if 'pasaporte' in cedula_or_passport.lower() or len(cedula_or_passport) > 10:
            if not re.match(r'^[A-Z0-9]{6,20}$', cedula_or_passport.upper()):
                return False, "El formato del pasaporte no es válido (debe ser alfanumérico, 6-20 caracteres)"

    if not re.match(r'^[A-Z0-9\-\s\.]{4,20}$', cedula_or_passport.upper()):
        return False, "El formato de cédula o pasaporte no es válido (debe ser alfanumérico)"

    return True, None


def generate_verification_token():
    """Generar token único para verificación de email."""
    return secrets.token_urlsafe(32)

