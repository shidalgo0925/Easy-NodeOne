"""Logos de tenant para email/nav: viven bajo static/uploads (gitignored), no bajo static/public."""

from __future__ import annotations

import glob
import os
import shutil

# Relativo al directorio static/ de Flask
TENANT_EMAIL_LOGO_REL_DIR = 'uploads/emails/logos'


def _static_root_abs() -> str:
    import app as M

    return os.path.normpath(os.path.join(os.path.dirname(M.__file__), '..', 'static'))


def tenant_email_logo_dir_abs() -> str:
    return os.path.join(_static_root_abs(), 'uploads', 'emails', 'logos')


def legacy_tenant_email_logo_dir_abs() -> str:
    return os.path.join(_static_root_abs(), 'public', 'emails', 'logos')


def resolve_tenant_logo_static_relpath(stored: str | None) -> str:
    """
    Si logo_url apunta a un fichero logo-email-org* bajo public/ y ya solo existe en uploads/, devuelve la ruta válida.
    No altera rutas que no son logos de tenant por org (p. ej. logo-primary).
    """
    s = (stored or '').strip().lstrip('/')
    if not s or 'logo-email-org' not in s:
        return s
    root = _static_root_abs()
    p1 = os.path.join(root, s.replace('/', os.sep))
    if os.path.isfile(p1):
        return s
    bn = os.path.basename(s.replace('\\', '/'))
    if not (bn.startswith('logo-email-org') and bn.endswith(('.png', '.svg', '.jpg', '.jpeg'))):
        return s
    alt = f'{TENANT_EMAIL_LOGO_REL_DIR}/{bn}'
    p2 = os.path.join(root, alt.replace('/', os.sep))
    if os.path.isfile(p2):
        return alt
    return s


def migrate_legacy_tenant_email_logos_to_uploads(db, printfn=None) -> None:
    """
    Mueve logo-email-org* de static/public/emails/logos a static/uploads/emails/logos
    y actualiza organization_settings.logo_url. Idempotente.
    """
    from models.saas import OrganizationSettings

    dest = tenant_email_logo_dir_abs()
    legacy = legacy_tenant_email_logo_dir_abs()
    os.makedirs(dest, exist_ok=True)

    for pattern in ('logo-email-org*.png', 'logo-email-org*.svg', 'logo-email-org*.jpg', 'logo-email-org*.jpeg'):
        for src in glob.glob(os.path.join(legacy, pattern)):
            bn = os.path.basename(src)
            dst = os.path.join(dest, bn)
            try:
                if os.path.exists(dst):
                    if os.path.exists(src):
                        os.remove(src)
                    if printfn:
                        printfn(f'📋 tenant logo: ya en uploads, eliminado legado {bn}')
                elif os.path.exists(src):
                    shutil.move(src, dst)
                    if printfn:
                        printfn(f'📋 tenant logo: migrado {bn} -> uploads/emails/logos/')
            except OSError as e:
                if printfn:
                    printfn(f'⚠️ tenant logo migrate {bn}: {e}')

    rows = (
        OrganizationSettings.query.filter(OrganizationSettings.logo_url.isnot(None))
        .filter(OrganizationSettings.logo_url != '')
        .filter(OrganizationSettings.logo_url.like('%public/emails/logos/logo-email-org%'))
        .all()
    )
    n = 0
    for r in rows:
        raw = (r.logo_url or '').strip().replace('\\', '/')
        bn = os.path.basename(raw)
        if bn.startswith('logo-email-org'):
            r.logo_url = f'{TENANT_EMAIL_LOGO_REL_DIR}/{bn}'
            n += 1
    if n:
        try:
            db.session.commit()
            if printfn:
                printfn(f'📋 organization_settings.logo_url actualizado ({n} filas) -> uploads/emails/logos/')
        except Exception:
            db.session.rollback()
            raise
