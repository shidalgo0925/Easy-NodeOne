"""Validación de archivo XLS/XLSX no confiable (sin ejecutar macros ni fórmulas)."""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from dataclasses import dataclass

XLSX_MAGIC = b'PK\x03\x04'
XLS_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
ALLOWED_EXT = ('.xlsx', '.xls')
BLOCKED_EXT = ('.xlsm', '.csv', '.xlsb')
_SAFE_NAME = re.compile(r'[^A-Za-z0-9._ -]+')


class XlsImportSecurityError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.user_message = message


@dataclass
class SafeWorkbook:
    filename: str
    sha256: str
    kind: str  # xlsx | xls
    payload: bytes


def max_bytes() -> int:
    raw = (os.environ.get('NODEONE_SALES_XLS_MAX_BYTES') or '').strip()
    try:
        n = int(raw) if raw else 8 * 1024 * 1024
    except ValueError:
        n = 8 * 1024 * 1024
    return max(1024, min(n, 32 * 1024 * 1024))


def sanitize_filename(name: str) -> str:
    base = os.path.basename((name or '').replace('\\', '/').replace('\x00', ''))
    base = _SAFE_NAME.sub('_', base).strip(' ._') or 'import.xlsx'
    return base[:180]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_upload(*, filename: str, data: bytes) -> SafeWorkbook:
    if not data:
        raise XlsImportSecurityError('empty_file', 'El archivo está vacío.')
    if len(data) > max_bytes():
        raise XlsImportSecurityError(
            'file_too_large',
            f'El archivo supera el tamaño máximo permitido ({max_bytes()} bytes).',
        )
    raw_name = filename or ''
    lower = raw_name.lower()
    if any(lower.endswith(ext) for ext in BLOCKED_EXT):
        raise XlsImportSecurityError('unsupported_type', 'Solo se permiten archivos .xls y .xlsx.')
    ext = ''
    for cand in ALLOWED_EXT:
        if lower.endswith(cand):
            ext = cand
            break
    if not ext:
        raise XlsImportSecurityError('unsupported_type', 'Solo se permiten archivos .xls y .xlsx.')

    head = data[:8]
    if ext == '.xlsx':
        if not data.startswith(XLSX_MAGIC):
            raise XlsImportSecurityError('invalid_content', 'El contenido no corresponde a un .xlsx válido.')
        _reject_xlsx_macros(data)
        kind = 'xlsx'
    else:
        if not head.startswith(XLS_MAGIC):
            raise XlsImportSecurityError('invalid_content', 'El contenido no corresponde a un .xls válido.')
        kind = 'xls'

    return SafeWorkbook(
        filename=sanitize_filename(raw_name),
        sha256=sha256_bytes(data),
        kind=kind,
        payload=data,
    )


def _reject_xlsx_macros(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [n.replace('\\', '/').lower() for n in zf.namelist()]
    except zipfile.BadZipFile as exc:
        raise XlsImportSecurityError('invalid_content', 'El .xlsx está dañado o no es un ZIP válido.') from exc
    if any(n.endswith('vbaproject.bin') or '/vba/' in n for n in names):
        raise XlsImportSecurityError('macros_not_allowed', 'No se permiten libros con macros.')
    if any('..' in n or n.startswith('/') for n in names):
        raise XlsImportSecurityError('invalid_content', 'El .xlsx contiene rutas no permitidas.')
