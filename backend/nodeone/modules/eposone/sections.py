"""Metadatos de secciones del back office EPosOne (Etapa 7)."""

from __future__ import annotations

# slug → (título, descripción corta)
EPOSONE_SECTIONS: dict[str, tuple[str, str]] = {
    'orders': ('Pedidos', 'Órdenes y tickets de venta en punto de venta.'),
    'contacts': ('Clientes', 'Contactos del POS — Cliente POS, Fiscal y Consumidor Final (maestro EN1).'),
    'products': ('Productos', 'Catálogo maestro de bienes y servicios para el POS.'),
    'inventory': ('Inventario', 'Stock y movimientos vinculados al POS.'),
    'branches': (
        'Sucursales',
        'Locales del negocio · cada sucursal agrupa POS y cajas.',
    ),
    'organization': (
        'Empresa',
        'Datos legales, zona horaria y moneda operativa del negocio.',
    ),
    'pos-points': (
        'Puntos de Venta',
        'POS del negocio · Sucursal → POS → Caja.',
    ),
    'terminals': ('Dispositivos', 'Tablets ya vinculadas a una caja.'),
    'registers': (
        'Cajas',
        'Cajas del POS (Administración). La tablet se vincula después en Instalar dispositivo.',
    ),
    'shifts': ('Turnos', 'Turnos de operadores y responsables de caja.'),
    'cashiers': ('Cajeros', 'Personal autorizado para operar turnos de caja.'),
    'promotions': ('Promociones', 'Descuentos, combos y reglas comerciales POS.'),
    'kds': ('Cocina (KDS)', 'Tickets de cocina y opciones del flujo KDS.'),
    'delivery': ('Delivery', 'Repartidores, rutas y estado de entrega.'),
    'digital-menu': ('Menú digital', 'Catálogo QR para pedidos del cliente.'),
    'licenses': (
        'Licencias',
        'Estado comercial por caja (informativo · no bloquea la preparación del negocio).',
    ),
}

EPOSONE_SECTION_SLUGS: frozenset[str] = frozenset(EPOSONE_SECTIONS.keys())
