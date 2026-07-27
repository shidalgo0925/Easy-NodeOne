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
            'Punto de venta todo en uno para retail, restaurantes y servicios: '
            'ventas, inventario, clientes y reportes. Online y offline. 45 días gratis.'
        ),
        'hero': {
            'eyebrow': 'EasyTech · Plataforma de punto de venta',
            'headline': name,
            'tagline': 'Vende más. Controla todo. Desde cualquier lugar.',
            'subhead': (
                'Punto de venta todo en uno para retail, restaurantes y servicios: '
                'gestione ventas, inventario, clientes y reportes con una interfaz intuitiva '
                'que funciona online y offline.'
            ),
            'offer_badge': '45 días gratis · Sin docs. fiscales ni firma electrónica',
            'primary_cta': {'label': 'Solicitar demostración', 'href': '#demo'},
            'secondary_cta': {'label': 'Ver planes', 'href': '#planes'},
            'tertiary_cta': {'label': 'Iniciar sesión', 'href': 'login'},
            'fine_print': (
                'Sin compromiso · La prueba no incluye documentos fiscales ni firma electrónica · Contacto EasyTech'
            ),
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
                    'title': 'Control total de inventario',
                    'body': 'Productos, variantes y stock en tiempo real con alertas automáticas.',
                },
                {
                    'title': 'Clientes y fidelización',
                    'body': 'Historial de compras, puntos y programas de lealtad integrados.',
                },
                {
                    'title': 'Reportes inteligentes',
                    'body': 'Ventas, productos, empleados y márgenes para decidir con datos.',
                },
                {
                    'title': 'Online y offline',
                    'body': 'Siga vendiendo sin internet; sincroniza automáticamente al reconectar.',
                },
            ],
        },
        'modules': {
            'title': 'Módulos principales',
            'lead': 'Seis módulos integrados para operar su negocio desde el mostrador hasta el backoffice.',
            'entries': [
                {'label': 'POS', 'title': 'Punto de venta', 'body': 'Ventas, descuentos, devoluciones y cobros en segundos.'},
                {'label': 'Stock', 'title': 'Inventario', 'body': 'Control de existencias, alertas, transferencias y variantes.'},
                {'label': 'CRM', 'title': 'Clientes', 'body': 'Base de datos, historial de compras y programas de fidelización.'},
                {'label': 'Marketing', 'title': 'Promociones', 'body': 'Descuentos, combos, cupones y campañas en mostrador.'},
                {'label': 'Datos', 'title': 'Reportes', 'body': 'Ventas, márgenes, productos top y desempeño por empleado.'},
                {'label': 'Admin', 'title': 'Configuración', 'body': 'Impuestos, usuarios, permisos y parámetros por sucursal.'},
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
            'Facturación electrónica — cumplimiento DGI Panamá (no incluida en los 45 días gratis; docs. fiscales y firma electrónica se habilitan aparte)',
            'Pasarelas de pago — Yappy, Telered, Stripe',
            'Contabilidad — Easy Odoo / ERP',
            'E-commerce — tiendas en línea conectadas',
        ],
        'offer_highlights': [
            {
                'title': '45 días gratis',
                'body': 'Sin tarjeta ni compromiso · No incluye docs. fiscales ni firma electrónica',
            },
            {'title': 'Implementación gratis', 'body': 'Capacitación incluida'},
            {'title': 'Cancela cuando quieras', 'body': 'Sin permanencia'},
        ],
        'plans_intro': (
            'Montos en USD. Incluye sincronización con EN1 y modo offline. '
            'La facturación electrónica Panamá está disponible en los planes; requiere alta DGI. '
            'Confirme vigencia con EasyTech.'
        ),
        'plans': [
            {
                'eyebrow': 'Ideal para un punto de venta',
                'name': 'Starter',
                'price': 'US$24.99',
                'period': '/ mes',
                'blurb': 'Ideal para cafeterías, tiendas y pequeños negocios.',
                'points': [
                    '1 POS',
                    'Caja',
                    'Pedidos',
                    'Inventario básico',
                    'Reportes',
                    'Offline',
                    'Módulo FE disponible*',
                    'Soporte',
                ],
                'cta': 'Solicitar plan',
            },
            {
                'eyebrow': 'Para la mayoría de los negocios',
                'name': 'Business',
                'price': 'US$34.99',
                'period': '/ mes',
                'blurb': 'Restaurantes, bares y comercios en crecimiento.',
                'points': [
                    'Hasta 3 POS',
                    'Inventario avanzado',
                    'Clientes',
                    'Dashboard EN1',
                    'Reportes avanzados',
                    'Sincronización',
                    'Módulo FE disponible*',
                    'Soporte prioritario',
                ],
                'featured': True,
                'cta': 'Solicitar plan',
            },
            {
                'eyebrow': 'Cadenas y múltiples sucursales',
                'name': 'Enterprise',
                'price': 'US$59.99',
                'period': '/ mes',
                'blurb': 'Negocios grandes que necesitan control total.',
                'points': [
                    'POS ilimitados',
                    'Multi sucursal',
                    'Dashboard corporativo',
                    'Roles avanzados',
                    'API',
                    'Reportes avanzados',
                    'Módulo FE disponible*',
                    'Soporte premium',
                ],
                'cta': 'Hablar con ventas',
            },
        ],
        'plan_compare': {
            'headers': ['Capacidad', 'Starter', 'Business', 'Enterprise'],
            'rows': [
                ['Precio mensual', 'US$24.99', 'US$34.99', 'US$59.99'],
                ['Terminales POS', '1', 'Hasta 3', 'Ilimitados'],
                ['Modo offline', 'Sí', 'Sí', 'Sí'],
                ['Inventario', 'Básico', 'Avanzado', 'Sí'],
                ['Dashboard EN1', '—', 'Sí', 'Corporativo'],
                ['Multi-sucursal', '—', '—', 'Sí'],
                ['API', '—', '—', 'Sí'],
                ['Módulo FE Panamá*', 'Disponible', 'Disponible', 'Disponible'],
                ['Soporte', 'Estándar', 'Prioritario', 'Premium'],
            ],
            'footnote': (
                '*Facturación electrónica: el período de 45 días gratis no incluye documentos fiscales '
                'ni firma electrónica (certificado / DGI). Esos servicios se habilitan aparte tras el onboarding. '
                'Implementación y capacitación del POS incluidas. Dispositivos e impresoras se cotizan aparte.'
            ),
        },
        'testimonials': {
            'title': 'Lo que dicen nuestros clientes',
            'note': 'La oferta de 45 días gratis aplica al POS. No incluye documentos fiscales ni firma electrónica.',
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
                'q': '¿Qué incluye la prueba de 45 días gratis?',
                'a': (
                    'El punto de venta (POS). No incluye documentos fiscales ni firma electrónica '
                    '(certificado / DGI); eso se habilita aparte tras el onboarding.'
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
                'Sin compromiso. Prueba de 45 días gratis del punto de venta. '
                'No incluye documentos fiscales ni firma electrónica.'
            ),
            'source': 'eposone-landing',
            'contacts': [
                {'label': 'WhatsApp +507 6688-4938', 'href': 'https://wa.me/50766884938'},
                {'label': 'Correo', 'href': 'mailto:info@easytech.services'},
            ],
        },
        'source_url': 'https://easytech.services/eposone.html',
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
