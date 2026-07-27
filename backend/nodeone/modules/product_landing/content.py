"""ADR-017 Hito 1 — copy comercial por producto (Portal Público).

EPosOne: alineado a https://easytech.services/eposone.html
"""

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
    name = display_name or 'EPosOne'
    return {
        'product_code': 'eposone',
        'template': 'product_landing/eposone.html',
        'meta_title': f'{name} — Punto de venta | EasyTech',
        'meta_description': (
            'Punto de venta moderno para Panamá: retail, restaurantes y servicios. '
            'Online y offline, sincronización con EN1. Prueba gratuita de 15 días.'
        ),
        'hero': {
            'eyebrow': 'Easy Technology Services',
            'headline': name,
            'tagline': 'Vende más. Controla todo. Desde cualquier lugar.',
            'subhead': (
                'El punto de venta inteligente que impulsa tu negocio. '
                'Todo en uno para retail, restaurantes y servicios: ventas, inventario, '
                'clientes y reportes — online y offline.'
            ),
            'offer_badge': '15 días gratis · Actualizaciones y soporte incluidos',
            'primary_cta': {'label': 'Solicitar demostración', 'href': '#demo'},
            'secondary_cta': {'label': 'Ver planes', 'href': '#planes'},
            'tertiary_cta': {'label': 'Iniciar sesión', 'href': 'login'},
            'fine_print': (
                'Sin compromiso · Suscripción con actualizaciones y soporte · Contacto EasyTech'
            ),
            'side_image': 'images/eposone-landing-hero-side.png',
            'side_image_alt': (
                'EPOSOne en punto de venta: café, terminal táctil y cobro con tarjeta'
            ),
        },
        'about': {
            'title_prefix': '¿Qué es',
            'title_brand': name,
            'lead': 'El punto de venta inteligente que impulsa tu negocio.',
            'image': 'images/eposone-landing-product.jpg',
            'image_alt': 'Tablet con la interfaz EPosOne — punto de venta inteligente',
        },
        'assets': {
            'wordmark': 'images/logo-eposone-wordmark.jpg',
            'product_shot': 'images/eposone-landing-product.jpg',
            'hero_side': 'images/eposone-landing-hero-side.png',
        },
        'pillars': [
            {'title': 'Más rápido', 'body': 'Cobros ágiles y menos filas en caja.'},
            {'title': 'Más control', 'body': 'Inventario y ventas en tiempo real.'},
            {'title': 'Más clientes', 'body': 'Fidelización y historial de compras.'},
            {'title': 'Más seguridad', 'body': 'Permisos, roles y trazabilidad.'},
            {'title': 'Desde cualquier lugar', 'body': 'Nube con modo offline incluido.'},
        ],
        'capabilities': {
            'title': 'Todo lo que necesita en caja',
            'entries': [
                {
                    'title': 'Ventas rápidas y flexibles',
                    'body': 'Interfaz intuitiva, descuentos, devoluciones y múltiples métodos de pago.',
                },
                {
                    'title': 'Productos y categorías',
                    'body': 'Catálogo en caja con control básico de productos incluido en el plan.',
                },
                {
                    'title': 'Clientes en caja',
                    'body': 'Registro de clientes en el POS. El módulo CRM completo es adicional.',
                },
                {
                    'title': 'Reportes de ventas',
                    'body': 'Ventas y operación diaria para decidir con datos. Reportes avanzados según plan.',
                },
                {
                    'title': 'Online y offline',
                    'body': 'Siga vendiendo sin internet; sincroniza automáticamente al reconectar.',
                },
            ],
        },
        'modules': {
            'title': 'Módulos',
            'lead': (
                'El plan incluye el POS core (caja, productos, ventas, reportes básicos y configuración). '
                'CRM, Marketing y el resto de módulos se contratan como adicionales.'
            ),
            'entries': [
                {
                    'label': 'POS',
                    'title': 'Punto de venta',
                    'body': 'Ventas, descuentos, devoluciones y cobros en segundos.',
                    'badge': 'Incluido',
                    'included': True,
                },
                {
                    'label': 'Stock',
                    'title': 'Inventario',
                    'body': 'Control avanzado de existencias, alertas, transferencias y variantes.',
                    'badge': 'Adicional',
                    'included': False,
                },
                {
                    'label': 'CRM',
                    'title': 'Clientes',
                    'body': 'Base de datos, historial de compras y programas de fidelización.',
                    'badge': 'Adicional',
                    'included': False,
                },
                {
                    'label': 'Marketing',
                    'title': 'Promociones',
                    'body': 'Descuentos, combos, cupones y campañas en mostrador.',
                    'badge': 'Adicional',
                    'included': False,
                },
                {
                    'label': 'Datos',
                    'title': 'Reportes avanzados',
                    'body': 'Márgenes, productos top y desempeño por empleado más allá del reporte de ventas del plan.',
                    'badge': 'Adicional',
                    'included': False,
                },
                {
                    'label': 'Admin',
                    'title': 'Configuración',
                    'body': 'Impuestos, usuarios, permisos y parámetros por sucursal.',
                    'badge': 'Incluido',
                    'included': True,
                },
            ],
        },
        'benefits_list': [
            'Aumente ventas y productividad del equipo',
            'Reduzca errores y mermas en caja',
            'Controle inventario en tiempo real',
            'Mejore la experiencia del cliente',
            'Tome decisiones informadas con reportes',
            'Escale de una sucursal a múltiples locales',
        ],
        'integrations': [
            'EasyNodeOne (EN1) — gestión administrativa y financiera',
            'Facturación electrónica — configuración DGI Panamá (servicio opcional)',
            'Pasarelas de pago — Yappy, Telered, Stripe',
            'Contabilidad — Easy Odoo / ERP',
            'E-commerce — tiendas en línea conectadas',
        ],
        'offer_highlights': [
            {
                'title': '15 días gratis',
                'body': 'Prueba el POS sin compromiso · Actualizaciones incluidas',
            },
            {'title': 'Implementación incluida', 'body': 'Configuración inicial y capacitación básica'},
            {'title': 'Licenciamiento EN1', 'body': 'Respaldo y administración desde la nube'},
        ],
        'plans_intro': (
            'EPOS One es un punto de venta moderno para Panamá, diseñado para trabajar incluso sin Internet, '
            'con sincronización inteligente hacia EN1, administración centralizada y un modelo de suscripción '
            'que incluye actualizaciones, soporte y evolución continua del producto. Montos en USD.'
        ),
        'plans': [
            {
                'eyebrow': 'Lanzamiento comercial',
                'name': 'EPOS One Business',
                'price': 'USD 39.95',
                'period': '/mes',
                'blurb': 'Ideal para pequeños y medianos negocios.',
                'points_heading': 'Incluye',
                'points': [
                    '1 organización',
                    '1 sucursal',
                    'Hasta 2 cajas POS',
                    'Usuarios/cajeros ilimitados',
                    'Productos y categorías',
                    'Clientes',
                    'Ventas',
                    'Tickets abiertos',
                    'Múltiples formas de pago',
                    'Arqueo y cierre de caja',
                    'Reportes de ventas',
                    'Impresión de recibos',
                    'Impuestos configurables',
                    'Propinas configurables',
                    'Modo Offline First',
                    'Sincronización con EN1',
                    'Actualizaciones incluidas',
                    'Soporte estándar',
                    'Prueba gratuita de 15 días',
                ],
                'featured': True,
                'cta': 'Solicitar plan',
            },
            {
                'eyebrow': 'Varias sucursales o mayor volumen',
                'name': 'EPOS One Enterprise',
                'price': 'USD 79.95',
                'period': '/mes',
                'blurb': 'Para empresas con varias sucursales o mayor volumen de operación.',
                'points_heading': 'Todo lo incluido en Business, más:',
                'points': [
                    'Sucursales múltiples',
                    'Cajas POS según el plan contratado',
                    'Administración centralizada',
                    'Reportes consolidados',
                    'Gestión avanzada de usuarios y permisos',
                    'APIs e integraciones',
                    'Prioridad en sincronización y soporte',
                    'Funciones Enterprise que se incorporen en futuras versiones',
                    'Asistencia prioritaria',
                    'Prueba gratuita de 15 días',
                ],
                'cta': 'Hablar con ventas',
            },
        ],
        'plan_compare': {
            'headers': ['Capacidad', 'Business', 'Enterprise'],
            'rows': [
                ['Precio mensual', 'USD 39.95', 'USD 79.95'],
                ['Organizaciones', '1', '1+'],
                ['Sucursales', '1', 'Múltiples'],
                ['Cajas POS', 'Hasta 2', 'Según plan contratado'],
                ['Usuarios/cajeros', 'Ilimitados', 'Ilimitados + permisos avanzados'],
                ['Modo Offline First', 'Sí', 'Sí'],
                ['Sincronización EN1', 'Sí', 'Prioritaria'],
                ['Reportes', 'Ventas', 'Consolidados'],
                ['APIs e integraciones', '—', 'Sí'],
                ['Soporte', 'Estándar', 'Prioritario'],
                ['Prueba gratuita', '15 días', '15 días'],
            ],
            'footnote': (
                'Ambos planes incluyen configuración inicial, capacitación básica, actualizaciones continuas, '
                'respaldo de configuración en EN1 y licenciamiento administrado desde EN1. '
                'CRM, Marketing, Inventario avanzado y demás módulos fuera del POS core se contratan como adicionales. '
                'Servicios como instalación en sitio, carga de catálogo, impresoras, facturación electrónica '
                'e integraciones personalizadas se cotizan aparte.'
            ),
        },
        'services_included': {
            'title': 'Servicios incluidos',
            'lead': 'En ambos planes:',
            'entries': [
                'Configuración inicial del sistema.',
                'Capacitación básica.',
                'Actualizaciones continuas.',
                'Respaldo de configuración en EN1.',
                'Licenciamiento administrado desde EN1.',
            ],
        },
        'services_optional': {
            'title': 'Servicios y módulos opcionales',
            'lead': 'Se cotizan aparte según necesidad:',
            'entries': [
                'Módulo CRM (adicional).',
                'Módulo Marketing (adicional).',
                'Módulos adicionales fuera del POS core (inventario avanzado, reportes avanzados, etc.).',
                'Instalación en sitio.',
                'Carga inicial del catálogo de productos.',
                'Configuración de impresoras.',
                'Configuración de facturación electrónica.',
                'Capacitación avanzada.',
                'Desarrollo de integraciones personalizadas.',
                'Migración desde otro sistema POS.',
            ],
        },
        'testimonials': {
            'title': 'Lo que dicen nuestros clientes',
            'note': 'Prueba gratuita de 15 días del POS. Actualizaciones y soporte incluidos en la suscripción.',
            'entries': [
                {
                    'quote': 'Tenemos control total de ventas e inventario. Tomamos mejores decisiones cada semana.',
                    'author': 'Juan R., Café Aroma',
                },
                {
                    'quote': 'Fácil de usar para el equipo y el stock se actualiza al instante.',
                    'author': 'María G., Boutique 21',
                },
                {
                    'quote': 'El modo offline nos salvó en horas pico del restaurante.',
                    'author': 'Carlos M., Sabor y Punto',
                },
            ],
        },
        'faq': [
            {
                'q': '¿Qué incluye la prueba gratuita de 15 días?',
                'a': (
                    'El punto de venta (POS) con las capacidades del plan elegido. '
                    'Servicios opcionales (instalación en sitio, facturación electrónica, migraciones, etc.) '
                    'se cotizan aparte.'
                ),
            },
            {
                'q': '¿EPosOne es aparte de Easy NodeOne?',
                'a': (
                    'Es un producto del ecosistema EasyTech. Corre sobre EN1: '
                    'misma cuenta, suscripciones y entitlements.'
                ),
            },
            {
                'q': '¿Cómo solicito una demo o un plan?',
                'a': 'Completá el formulario en esta página o escribinos por WhatsApp / correo a EasyTech.',
            },
            {
                'q': '¿Ya soy cliente? ¿Dónde entro?',
                'a': 'Usá «Iniciar sesión». Si solo tenés EPosOne, vas al producto; si tenés varios, al Portal de cuenta.',
            },
        ],
        'demo': {
            'title': 'Solicite una demostración de EPosOne',
            'subtitle': (
                'Sin compromiso. Prueba gratuita de 15 días del punto de venta. '
                'Actualizaciones y soporte incluidos en la suscripción.'
            ),
            'source': 'eposone-landing',
            'contacts': [
                {'label': 'WhatsApp +507 6688-4938', 'href': 'https://wa.me/50766884938'},
                {'label': 'Correo', 'href': 'mailto:info@easytech.services'},
            ],
        },
        'source_url': 'https://easytech.services/eposone.html',
        'tagline': tagline or 'Punto de venta inteligente',
        'description': description,
        'logo_wide': True,
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
