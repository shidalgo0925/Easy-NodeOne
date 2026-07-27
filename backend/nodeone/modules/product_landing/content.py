"""ADR-017 Hito 1 — copy comercial por producto (Portal Público)."""

from __future__ import annotations

from typing import Any


def landing_content_for(product_code: str, *, display_name: str, tagline: str, description: str) -> dict[str, Any]:
    """Contenido de landing. EPosOne tiene página completa; otros productos usan plantilla genérica."""
    code = (product_code or '').strip().lower()
    if code == 'eposone':
        return _eposone_content(display_name=display_name, tagline=tagline, description=description)
    return _generic_product_content(
        code=code,
        display_name=display_name,
        tagline=tagline,
        description=description,
    )


def _eposone_content(*, display_name: str, tagline: str, description: str) -> dict[str, Any]:
    return {
        'product_code': 'eposone',
        'template': 'product_landing/eposone.html',
        'meta_title': f'{display_name} — Punto de venta para tu negocio',
        'meta_description': (
            'EPosOne es el punto de venta y operación de caja de Easy Technology Services. '
            'Mesas, llevar, delivery, menú digital y control comercial en una sola plataforma.'
        ),
        'hero': {
            'eyebrow': 'Easy Technology Services',
            'headline': display_name,
            'subhead': (
                'Punto de venta pensado para restaurantes y comercios: '
                'caja, mesas, pedidos y menú digital, conectados a tu cuenta ETS.'
            ),
            'primary_cta': {'label': 'Solicitar demo', 'href': '#demo'},
            'secondary_cta': {'label': 'Iniciar sesión', 'href': 'login'},
        },
        'benefits': [
            {
                'title': 'Operación de caja clara',
                'body': 'Apertura, ventas y cierre con trazabilidad. Menos fricción en el turno.',
            },
            {
                'title': 'Mesas, llevar y delivery',
                'body': 'Flujos de pedido alineados al día a día del local, no a un ERP genérico.',
            },
            {
                'title': 'Menú digital',
                'body': 'Carta pública con categorías e imágenes, lista para compartir por QR.',
            },
            {
                'title': 'Parte del ecosistema ETS',
                'body': 'Misma cuenta, suscripciones y entitlements. Crece a EPayRoll y más sin cambiar de plataforma.',
            },
        ],
        'plans': [
            {
                'name': 'Starter',
                'blurb': 'Un punto de venta para empezar con orden.',
                'points': ['1 POS', 'Caja y pedidos', 'Menú digital básico', 'Soporte estándar'],
            },
            {
                'name': 'Professional',
                'blurb': 'Para locales con más operación y canales.',
                'points': ['Varios POS', 'Mesas / llevar / delivery', 'Menú digital ampliado', 'Prioridad en soporte'],
                'featured': True,
            },
            {
                'name': 'Enterprise',
                'blurb': 'Multi-local y capacidades a medida.',
                'points': ['Cupos negociados', 'Integraciones', 'Onboarding dedicado', 'SLA acordado'],
            },
        ],
        'faq': [
            {
                'q': '¿EPosOne es una app aparte de Easy NodeOne?',
                'a': (
                    'EPosOne es un producto del ecosistema ETS. Corre sobre la plataforma EN1: '
                    'una sola cuenta, identidad y suscripciones.'
                ),
            },
            {
                'q': '¿Cómo solicito una demo?',
                'a': 'Completá el formulario en esta página. El equipo ETS te contacta para una sesión guiada.',
            },
            {
                'q': '¿Ya soy cliente? ¿Dónde entro?',
                'a': 'Usá «Iniciar sesión». Si solo tenés EPosOne, vas directo al producto; si tenés varios, al Portal de cuenta.',
            },
            {
                'q': '¿Sirve para restaurantes y comercios?',
                'a': 'Sí. El foco actual es operación de venta y caja; el alcance crece según el plan contratado.',
            },
        ],
        'demo': {
            'title': 'Solicitar demo',
            'subtitle': 'Contanos de tu negocio. Te contactamos para una demostración.',
            'source': 'eposone-landing',
        },
        'tagline': tagline or 'Punto de venta',
        'description': description,
    }


def _generic_product_content(
    *,
    code: str,
    display_name: str,
    tagline: str,
    description: str,
) -> dict[str, Any]:
    name = display_name or code or 'Producto'
    return {
        'product_code': code,
        'template': 'product_landing/generic.html',
        'meta_title': f'{name} — Easy Technology Services',
        'meta_description': (description or tagline or name)[:160],
        'hero': {
            'eyebrow': 'Easy Technology Services',
            'headline': name,
            'subhead': description or tagline or f'{name} en la plataforma ETS.',
            'primary_cta': {'label': 'Solicitar demo', 'href': '#demo'},
            'secondary_cta': {'label': 'Iniciar sesión', 'href': 'login'},
        },
        'benefits': [
            {
                'title': 'Integrado al ecosistema ETS',
                'body': 'Misma cuenta, portal y suscripciones que el resto de productos Easy Technology.',
            },
            {
                'title': 'Identidad propia',
                'body': f'{name} tiene su dominio y experiencia, sin duplicar la plataforma.',
            },
        ],
        'plans': [],
        'faq': [
            {
                'q': '¿Cómo obtengo acceso?',
                'a': 'Solicitá una demo o iniciá sesión si ya tenés cuenta ETS.',
            },
        ],
        'demo': {
            'title': 'Solicitar demo',
            'subtitle': f'Dejanos tus datos para conocer {name}.',
            'source': f'{code or "product"}-landing',
        },
        'tagline': tagline,
        'description': description,
    }
