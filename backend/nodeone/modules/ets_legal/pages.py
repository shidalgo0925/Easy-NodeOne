"""Centro legal ETS — páginas públicas compartidas (landing EPosOne / Portal).

Rutas canónicas en EN1:
  /legal/
  /legal/terms
  /legal/privacy
  /legal/cookies
  /legal/eula
  /legal/refunds
  /legal/ip
  /legal/data-deletion
  /legal/support

Dominio recomendado a futuro: legal.easytech.services o easytech.services/legal/
(mientras tanto se sirven desde el mismo host del producto, p. ej. eposone.easytech.services).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalPage:
    slug: str
    title: str
    nav_label: str
    summary: str
    audience: str  # 'all' | 'eposone'


LEGAL_PAGES: tuple[LegalPage, ...] = (
    LegalPage(
        slug='terms',
        title='Términos y Condiciones',
        nav_label='Términos y Condiciones',
        summary='Condiciones de uso de los servicios SaaS de Easy Technology Services.',
        audience='all',
    ),
    LegalPage(
        slug='privacy',
        title='Política de Privacidad',
        nav_label='Privacidad',
        summary='Cómo recopilamos, usamos y protegemos datos personales y comerciales.',
        audience='all',
    ),
    LegalPage(
        slug='cookies',
        title='Política de Cookies',
        nav_label='Cookies',
        summary='Uso de cookies y tecnologías similares en sitios y aplicaciones ETS.',
        audience='all',
    ),
    LegalPage(
        slug='eula',
        title='Acuerdo de Licencia de Usuario Final (EULA) — EPosOne',
        nav_label='EULA EPosOne',
        summary='Licencia de uso de la aplicación EPosOne (APK / cliente local).',
        audience='eposone',
    ),
    LegalPage(
        slug='refunds',
        title='Política de Reembolsos',
        nav_label='Reembolsos',
        summary='Condiciones de reembolso y cancelación de suscripciones.',
        audience='all',
    ),
    LegalPage(
        slug='ip',
        title='Aviso de Propiedad Intelectual',
        nav_label='Propiedad intelectual',
        summary='Marcas, software y contenidos de Easy Technology Services.',
        audience='all',
    ),
    LegalPage(
        slug='data-deletion',
        title='Eliminación de cuenta y datos',
        nav_label='Eliminación de datos',
        summary='Cómo solicitar baja de cuenta y eliminación de datos personales.',
        audience='all',
    ),
    LegalPage(
        slug='support',
        title='Contacto de soporte',
        nav_label='Soporte',
        summary='Canales de soporte comercial y técnico.',
        audience='all',
    ),
)


def get_legal_page(slug: str) -> LegalPage | None:
    key = (slug or '').strip().lower()
    for page in LEGAL_PAGES:
        if page.slug == key:
            return page
    return None
