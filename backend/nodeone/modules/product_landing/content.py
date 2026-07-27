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
            {'title': 'Escalera clara', 'body': 'Starter → Business → Enterprise'},
        ],
        'plans_intro': (
            'EPOS One es un punto de venta moderno para Panamá, diseñado para trabajar incluso sin Internet, '
            'con sincronización inteligente hacia EN1, administración centralizada y un modelo de suscripción '
            'que incluye actualizaciones, soporte y evolución continua del producto. '
            'Starter permite comenzar con una inversión accesible, Business cubre la mayoría de los restaurantes '
            'y comercios, y Enterprise queda orientado a operaciones con varias sucursales o requerimientos corporativos. '
            'Montos en USD.'
        ),
        'plans': [
            {
                'eyebrow': 'Emprendedores y pequeños comercios',
                'name': 'Starter',
                'price': 'USD 29.95',
                'period': '/mes',
                'blurb': (
                    'Ideal para emprendedores y pequeños comercios que necesitan un punto de venta '
                    'profesional, sencillo y confiable.'
                ),
                'points_heading': 'Incluye',
                'points': [
                    '1 sucursal',
                    '1 caja POS',
                    'Usuarios y cajeros ilimitados',
                    'Gestión de productos y categorías',
                    'Gestión de clientes',
                    'Ventas y tickets abiertos',
                    'Múltiples formas de pago',
                    'Impresión de recibos',
                    'Arqueo y cierre de caja',
                    'Reportes básicos',
                    'Configuración de impuestos',
                    'Modo Offline First',
                    'Sincronización con EN1',
                    'Actualizaciones incluidas',
                    'Soporte estándar',
                    'Prueba gratuita de 15 días',
                ],
                'cta': 'Solicitar plan',
            },
            {
                'eyebrow': 'Restaurantes, cafeterías y comercios establecidos',
                'name': 'Business',
                'price': 'USD 49.95',
                'period': '/mes',
                'blurb': 'Ideal para restaurantes, cafeterías y comercios con mayor volumen de ventas.',
                'points_heading': 'Todo lo incluido en Starter, más:',
                'points': [
                    'Hasta 2 cajas POS',
                    'Reportes avanzados',
                    'Configuración de propinas',
                    'Configuración avanzada de impuestos',
                    'Mayor capacidad operativa',
                    'Mejoras continuas del plan Business',
                    'Actualizaciones incluidas',
                    'Soporte estándar',
                    'Prueba gratuita de 15 días',
                ],
                'featured': True,
                'cta': 'Solicitar plan',
            },
            {
                'eyebrow': 'Múltiples sucursales o necesidades avanzadas',
                'name': 'Enterprise',
                'price': 'USD 79.95',
                'period': '/mes',
                'blurb': 'Ideal para empresas con múltiples sucursales o necesidades avanzadas de operación.',
                'points_heading': 'Todo lo incluido en Business, más:',
                'points': [
                    'Múltiples sucursales',
                    'Varias cajas POS (según la licencia contratada)',
                    'Administración centralizada',
                    'Reportes consolidados por sucursal',
                    'Gestión avanzada de usuarios y permisos',
                    'APIs e integraciones',
                    'Soporte prioritario',
                    'Acceso a funcionalidades Enterprise',
                    'Actualizaciones incluidas',
                    'Prueba gratuita de 15 días',
                    'Atención prioritaria',
                ],
                'cta': 'Hablar con ventas',
            },
        ],
        'plan_compare': {
            'headers': ['Plan', 'Starter', 'Business', 'Enterprise'],
            'rows': [
                ['Precio mensual', 'USD 29.95', 'USD 49.95', 'USD 79.95'],
                ['Ideal para', 'Emprendedores y pequeños comercios', 'Restaurantes, cafeterías y comercios establecidos', 'Múltiples sucursales o necesidades avanzadas'],
                ['Sucursales', '1', '1', 'Múltiples'],
                ['Cajas POS', '1', 'Hasta 2', 'Según licencia'],
                ['Usuarios/cajeros', 'Ilimitados', 'Ilimitados', 'Ilimitados + permisos avanzados'],
                ['Reportes', 'Básicos', 'Avanzados', 'Consolidados por sucursal'],
                ['Propinas', '—', 'Sí', 'Sí'],
                ['Modo Offline First', 'Sí', 'Sí', 'Sí'],
                ['Sincronización EN1', 'Sí', 'Sí', 'Prioritaria'],
                ['APIs e integraciones', '—', '—', 'Sí'],
                ['Soporte', 'Estándar', 'Estándar', 'Prioritario'],
                ['Prueba gratuita', '15 días', '15 días', '15 días'],
            ],
            'footnote': (
                'CRM, Marketing e inventario avanzado fuera del POS core se contratan como módulos adicionales. '
                'Facturación electrónica, instalación en sitio e integraciones a medida son servicios opcionales.'
            ),
        },
        'services_included': {
            'title': 'Servicios incluidos en todos los planes',
            'lead': '',
            'entries': [
                'Configuración inicial del sistema.',
                'Capacitación básica.',
                'Actualizaciones continuas.',
                'Licenciamiento administrado desde EN1.',
                'Seguridad y sincronización de datos.',
                'Plataforma preparada para crecer junto con el negocio.',
            ],
        },
        'services_optional': {
            'title': 'Servicios opcionales',
            'lead': 'Se cotizan aparte según necesidad:',
            'entries': [
                'Instalación en sitio.',
                'Configuración de impresoras y periféricos.',
                'Carga inicial del catálogo de productos.',
                'Configuración de facturación electrónica.',
                'Capacitación personalizada.',
                'Migración desde otro sistema POS.',
                'Integraciones a medida.',
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
