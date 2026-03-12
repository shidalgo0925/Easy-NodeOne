# Lógica del carrito (get_or_create, add_to_cart, resolve product para cart/add).
import hashlib

from app import Event, Service

from . import repository


def get_or_create_cart(user_id):
    """Obtener o crear carrito para el usuario (API usada por app y otros módulos)."""
    return repository.get_or_create_cart(user_id)


def add_to_cart(user_id, product_type, product_id, product_name, unit_price, quantity=1, product_description=None, metadata=None):
    """Agregar producto al carrito (API usada por app y otros módulos)."""
    cart = repository.get_or_create_cart(user_id)
    return repository.add_item(cart.id, product_type, product_id, product_name, unit_price, quantity, product_description, metadata)


def resolve_product_for_cart(user, data):
    """
    Resuelve product_id, product_name, product_description, unit_price, metadata desde data (request).
    Retorna (product_id, product_name, product_description, unit_price, metadata) o (None, error_dict, status_code).
    """
    product_type = data.get('product_type')
    quantity = int(data.get('quantity', 1))

    if product_type not in ['membership', 'event', 'service']:
        return None, {'success': False, 'error': 'Tipo de producto inválido'}, 400

    if product_type == 'membership':
        active_membership = user.get_active_membership()
        if active_membership:
            membership_type_requested = data.get('membership_type')
            if membership_type_requested == active_membership.membership_type:
                return None, {
                    'success': False,
                    'error': f'Ya tienes una membresía {membership_type_requested.title()} activa'
                }, 400
        membership_type = data.get('membership_type')
        if not membership_type:
            return None, {'success': False, 'error': 'Tipo de membresía no especificado'}, 400
        prices = {'basic': 0, 'pro': 6000, 'premium': 12000, 'deluxe': 20000}
        unit_price = prices.get(membership_type, 0)
        product_name = f"Membresía {membership_type.title()}"
        product_description = f"Plan de membresía {membership_type.title()} - 1 año"
        metadata = {'membership_type': membership_type}
        product_id = int(hashlib.md5(membership_type.encode()).hexdigest()[:8], 16) % 1000000
        return (product_id, product_name, product_description, unit_price, metadata), None, None

    if product_type == 'event':
        product_id = int(data.get('product_id', 0))
        if product_id == 0:
            return None, {'success': False, 'error': 'ID de evento no especificado'}, 400
        event = Event.query.get(product_id)
        if not event:
            return None, {'success': False, 'error': 'Evento no encontrado'}, 404
        active_membership = user.get_active_membership()
        membership_type = active_membership.membership_type if active_membership else 'basic'
        pricing = event.pricing_for_membership(membership_type)
        unit_price = int(pricing['final_price'] * 100)
        product_name = event.title
        product_description = event.summary or (event.description[:200] if event.description else "")
        metadata = {
            'event_id': event.id,
            'event_slug': event.slug,
            'base_price': pricing['base_price'],
            'final_price': pricing['final_price'],
            'discount_applied': pricing['discount'] is not None
        }
        return (product_id, product_name, product_description, unit_price, metadata), None, None

    if product_type == 'service':
        product_id = int(data.get('product_id', 0))
        if product_id == 0:
            return None, {'success': False, 'error': 'ID de servicio no especificado'}, 400
        service = Service.query.get(product_id)
        if not service:
            return None, {'success': False, 'error': 'Servicio no encontrado'}, 404
        active_membership = user.get_active_membership()
        membership_type = active_membership.membership_type if active_membership else 'basic'
        pricing = service.pricing_for_membership(membership_type)
        final_price = pricing['final_price']
        unit_price = int(final_price * 100)
        product_name = service.name
        product_description = service.description or 'Servicio de RELATIC'
        metadata = {
            'service_id': service.id,
            'base_price': pricing['base_price'],
            'final_price': pricing['final_price'],
            'discount_percentage': pricing['discount_percentage'],
            'is_included': pricing['is_included'],
            'membership_type': membership_type,
            'discount_applied': pricing['discount_percentage'] > 0,
            'requires_diagnostic': service.requires_diagnostic_appointment
        }
        return (product_id, product_name, product_description, unit_price, metadata), None, None

    return None, {'success': False, 'error': 'Tipo de producto inválido'}, 400


def remove_item(user_id, item_id):
    """Eliminar item del carrito. Retorna (cart, None) o (None, error_dict, 404)."""
    cart = repository.get_or_create_cart(user_id)
    cart_after = repository.remove_item(cart.id, item_id)
    if cart_after is None:
        return None, {'success': False, 'error': 'Item no encontrado'}, 404
    return cart_after, None


def update_item(user_id, item_id, quantity):
    """Actualizar cantidad. Retorna (cart, item, None, None) o (None, None, error_dict, status_code)."""
    if quantity < 1:
        return None, None, {'success': False, 'error': 'La cantidad debe ser al menos 1'}, 400
    cart = repository.get_or_create_cart(user_id)
    result = repository.update_item_quantity(cart.id, item_id, quantity)
    if result is None:
        return None, None, {'success': False, 'error': 'Item no encontrado'}, 404
    cart_after, item = result
    return cart_after, item, None, None


def get_checkout_data(user_id):
    """Datos para la página checkout. Retorna (cart, total_amount, discount_breakdown) o (None, redirect_endpoint) si carrito vacío."""
    cart = repository.get_or_create_cart(user_id)
    if cart.get_items_count() == 0:
        return None, 'payments.cart'
    breakdown = cart.get_discount_breakdown()
    total_amount = breakdown['final_total']
    return cart, total_amount, breakdown


def add_membership_to_cart_and_checkout(user_id, membership_type):
    """Agrega membresía al carrito (para checkout directo). membership_type válido: basic, pro, premium, deluxe, corporativo."""
    import hashlib
    prices = {'basic': 0, 'pro': 6000, 'premium': 12000, 'deluxe': 20000, 'corporativo': 30000}
    if membership_type not in prices:
        return None, 'membership'  # redirect to membership page
    product_id = int(hashlib.md5(membership_type.encode()).hexdigest()[:8], 16) % 1000000
    add_to_cart(
        user_id,
        'membership',
        product_id,
        f"Membresía {membership_type.title()}",
        prices[membership_type],
        1,
        f"Plan de membresía {membership_type.title()} - 1 año",
        {'membership_type': membership_type}
    )
    return 'payments.checkout', None


def _breakdown_to_dict(breakdown):
    return {
        'subtotal': breakdown['subtotal'],
        'master_discount_amount': breakdown['master_discount']['amount'] if breakdown.get('master_discount') else 0,
        'code_discount_amount': breakdown['code_discount']['amount'] if breakdown.get('code_discount') else 0,
        'total_discount': breakdown['total_discount'],
        'final_total': breakdown['final_total']
    }


def apply_discount_code(user_id, code):
    """Aplica código de descuento al carrito. Retorna (success, message, breakdown_dict) o (False, message, None)."""
    code = (code or '').strip().upper()
    if not code:
        return False, 'El código es requerido', None
    cart = repository.get_or_create_cart(user_id)
    success, message = cart.apply_discount_code(code)
    if not success:
        return False, message, None
    breakdown = cart.get_discount_breakdown()
    return True, message, _breakdown_to_dict(breakdown)


def remove_discount_code(user_id):
    """Quita el código de descuento del carrito. Retorna breakdown_dict."""
    cart = repository.get_or_create_cart(user_id)
    cart.remove_discount_code()
    breakdown = cart.get_discount_breakdown()
    return _breakdown_to_dict(breakdown)
