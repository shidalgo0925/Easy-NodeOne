"""ADR-017 Hito 1 — copy comercial por producto (Portal Público).

EPosOne: alineado a https://eposone.easytech.services/ (planes + ADR-023 trial/grace).
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
            'offer_badge': '15 días gratis en planes conectados · Sin tarjeta',
            'primary_cta': {'label': 'Solicitar demostración', 'href': '#demo'},
            'secondary_cta': {'label': 'Ver planes', 'href': '#planes'},
            'tertiary_cta': {'label': 'Iniciar sesión', 'href': 'login'},
            'fine_print': (
                'Prueba completa del plan · Grace 7 días ante demoras de pago · Contacto EasyTech'
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
        'integrations_title': 'Integraciones disponibles',
        'integrations': [
            'Facturación electrónica para Panamá',
            'Yappy',
            'Telered',
            'Stripe',
            'Sistemas contables y ERP',
            'Tiendas en línea',
            'APIs e integraciones empresariales',
        ],
        'integrations_footnote': (
            'Algunas integraciones requieren configuración, validación o contratación adicional. '
            'El módulo de facturación electrónica se habilita por separado después del proceso de '
            'configuración y validación correspondiente.'
        ),
        'offer_highlights': [
            {
                'title': '15 días gratis',
                'body': 'Starter, Business y Enterprise · Sin tarjeta · Funciones completas del plan',
            },
            {
                'title': 'Grace 7 días',
                'body': 'Ante demoras de pago · La suspensión no elimina tus datos',
            },
            {
                'title': 'Misma instalación',
                'body': 'Si te suscribes tras el trial, continúas sin reinstalar',
            },
        ],
        'plans_section_title': 'Planes',
        'plans_intro': (
            'Prueba EPOSOne gratis durante 15 días en Starter, Business y Enterprise. '
            'Sin tarjeta y con todas las funciones del plan seleccionado. '
            'Standalone: activación inmediata al contratar.'
        ),
        'plans_intro_extra': (
            'En planes conectados: producto completo sin tarjeta. Si te suscribes, continúas con la misma '
            'instalación. Hay 7 días de gracia ante demoras de pago; la suspensión no elimina automáticamente '
            'tus datos.'
        ),
        'plans': [
            {
                'eyebrow': 'Modalidad local',
                'name': 'Standalone',
                'price': 'USD 15.00',
                'period': '/mes',
                'badge': 'Activación al contratar · Sin prueba automática',
                'blurb': 'Ideal para pequeños comercios con un solo punto de venta.',
                'points_heading': 'Incluye',
                'points': [
                    '1 POS',
                    '1 caja',
                    'Ventas',
                    'Pedidos',
                    'Productos',
                    'Clientes',
                    'Inventario básico',
                    'Apertura y cierre de caja',
                    'Arqueo',
                    'Reportes básicos',
                    'Impresión',
                    'Operación local',
                    'Funciona sin conexión permanente',
                    'Almacenamiento local',
                    'Soporte estándar',
                ],
                'cta': 'Contratar Standalone',
                'legal_html': True,
                'legal_links': [
                    {'label': 'EULA', 'slug': 'eula'},
                    {'label': 'Términos', 'slug': 'terms'},
                ],
            },
            {
                'eyebrow': 'Modalidad conectada',
                'name': 'Starter',
                'price': 'USD 29.95',
                'period': '/mes',
                'badge': '15 días gratis',
                'blurb': (
                    'Para emprendedores y pequeños comercios que desean empezar con control y respaldo.'
                ),
                'points_heading': 'Incluye',
                'points': [
                    '1 POS',
                    'Caja',
                    'Pedidos',
                    'Productos',
                    'Clientes',
                    'Inventario básico',
                    'Reportes',
                    'Operación offline',
                    'Sincronización',
                    'Respaldo en la nube',
                    'Administración web',
                    'Soporte estándar',
                ],
                'cta': 'Probar gratis',
                'legal_links': [
                    {'label': 'Términos', 'slug': 'terms'},
                    {'label': 'EULA', 'slug': 'eula'},
                ],
            },
            {
                'eyebrow': 'Más elegido · Conectada',
                'name': 'Business',
                'price': 'USD 39.95',
                'period': '/mes',
                'badge': '15 días gratis',
                'blurb': 'Para restaurantes, cafeterías y comercios en crecimiento.',
                'points_heading': 'Incluye',
                'points': [
                    'Hasta 3 POS',
                    'Todo lo incluido en Starter',
                    'Inventario avanzado',
                    'Gestión de clientes',
                    'Reportes avanzados',
                    'Administración centralizada',
                    'Sincronización entre dispositivos',
                    'Acceso remoto',
                    'Soporte prioritario',
                ],
                'featured': True,
                'cta': 'Probar gratis',
                'legal_links': [
                    {'label': 'Términos', 'slug': 'terms'},
                    {'label': 'EULA', 'slug': 'eula'},
                ],
            },
            {
                'eyebrow': 'Multi-sucursal · Conectada',
                'name': 'Enterprise',
                'price': 'USD 79.95',
                'period': '/mes',
                'badge': '15 días gratis',
                'blurb': 'Para empresas con múltiples sucursales o necesidades avanzadas.',
                'points_heading': 'Incluye',
                'points': [
                    'Múltiples POS',
                    'Múltiples sucursales',
                    'Todo lo incluido en Business',
                    'Dashboard corporativo',
                    'Roles avanzados',
                    'Reportes consolidados',
                    'API',
                    'Integraciones empresariales',
                    'Soporte premium',
                ],
                'cta': 'Hablar con ventas',
                'legal_links': [
                    {'label': 'Términos', 'slug': 'terms'},
                    {'label': 'EULA', 'slug': 'eula'},
                ],
            },
        ],
        'plan_compare': {
            'title': 'Comparación de planes EPOSOne',
            'headers': ['Capacidad', 'Standalone', 'Starter', 'Business', 'Enterprise'],
            'rows': [
                ['Precio mensual', 'USD 15.00', 'USD 29.95', 'USD 39.95', 'USD 79.95'],
                ['Prueba de 15 días', 'No', 'Sí', 'Sí', 'Sí'],
                ['Dispositivos POS', '1', '1', 'Hasta 3', 'Múltiples'],
                ['Operación offline', 'Sí', 'Sí', 'Sí', 'Sí'],
                ['Administración web', 'No', 'Sí', 'Sí', 'Sí'],
                ['Respaldo en la nube', 'No', 'Sí', 'Sí', 'Sí'],
                ['Inventario', 'Básico', 'Básico', 'Avanzado', 'Avanzado'],
                ['Multi-sucursal', 'No', 'No', 'No', 'Sí'],
                ['API', 'No', 'No', 'No', 'Sí'],
                ['Soporte', 'Estándar', 'Estándar', 'Prioritario', 'Premium'],
            ],
            'footnote': (
                'Las capacidades específicas pueden variar según configuración, disponibilidad técnica '
                'y condiciones comerciales vigentes.'
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
                    'En Starter, Business y Enterprise: el POS con todas las funciones del plan, sin tarjeta. '
                    'Standalone no incluye prueba automática (activación al contratar). '
                    'Si te suscribes después del trial, continúas con la misma instalación.'
                ),
            },
            {
                'q': '¿Qué pasa si no pago al terminar el trial?',
                'a': (
                    'Hay 7 días de gracia con el sistema operativo y avisos. '
                    'Si no hay pago, la licencia se suspende: no permite nuevas operaciones comerciales, '
                    'pero no elimina automáticamente tus datos.'
                ),
            },
            {
                'q': '¿EPosOne es aparte de Easy NodeOne?',
                'a': (
                    'Es un producto del ecosistema EasyTech. Los planes conectados corren sobre EN1: '
                    'misma cuenta, suscripciones y entitlements. Standalone opera en modalidad local.'
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
                'Sin compromiso. Prueba gratuita de 15 días en planes conectados. '
                'Producto completo del plan · Sin tarjeta.'
            ),
            'source': 'eposone-landing',
            'contacts': [
                {'label': 'WhatsApp +507 6688-4938', 'href': 'https://wa.me/50766884938'},
                {'label': 'Correo', 'href': 'mailto:info@easytech.services'},
            ],
        },
        'source_url': 'https://eposone.easytech.services/',
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
