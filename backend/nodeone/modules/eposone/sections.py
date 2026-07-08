"""Metadatos de secciones del back office EPosOne (Etapa 7)."""

from __future__ import annotations

# slug → (título, descripción corta)
EPOSONE_SECTIONS: dict[str, tuple[str, str]] = {
    'orders': ('Pedidos', 'Órdenes y tickets de venta en punto de venta.'),
    'inventory': ('Inventario', 'Stock y movimientos vinculados al POS.'),
    'branches': ('Sucursales', 'Locales y puntos de operación comercial.'),
    'terminals': ('Terminales', 'Dispositivos y estaciones de cobro.'),
    'registers': ('Cajas', 'Apertura, cierre y arqueo de caja.'),
    'shifts': ('Turnos', 'Turnos de operadores y responsables de caja.'),
    'promotions': ('Promociones', 'Descuentos, combos y reglas comerciales POS.'),
    'kds': ('KDS', 'Pantalla de cocina, bar y runner — tickets en tiempo real.'),
    'delivery': ('Delivery', 'Repartidores, rutas y estado de entrega.'),
    'digital-menu': ('Menú digital', 'Catálogo QR para pedidos del cliente.'),
    'settings': ('Configuración', 'Parámetros operativos de EPosOne.'),
}

EPOSONE_SECTION_SLUGS: frozenset[str] = frozenset(EPOSONE_SECTIONS.keys())
