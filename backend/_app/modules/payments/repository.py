# Acceso a datos del carrito.
from datetime import datetime
import json

from app import db, Cart, CartItem


def get_cart_by_user(user_id):
    return Cart.query.filter_by(user_id=user_id).first()


def create_cart(user_id):
    cart = Cart(user_id=user_id)
    db.session.add(cart)
    db.session.commit()
    return cart


def get_or_create_cart(user_id):
    cart = get_cart_by_user(user_id)
    if not cart:
        cart = create_cart(user_id)
    return cart


def find_cart_item(cart_id, product_type, product_id):
    return CartItem.query.filter_by(
        cart_id=cart_id,
        product_type=product_type,
        product_id=product_id
    ).first()


def add_item(cart_id, product_type, product_id, product_name, unit_price, quantity=1, product_description=None, metadata=None):
    existing = find_cart_item(cart_id, product_type, product_id)
    if existing:
        existing.quantity += quantity
        existing.updated_at = datetime.utcnow()
    else:
        metadata_json = json.dumps(metadata) if metadata else None
        new_item = CartItem(
            cart_id=cart_id,
            product_type=product_type,
            product_id=product_id,
            product_name=product_name,
            product_description=product_description,
            unit_price=unit_price,
            quantity=quantity,
            item_metadata=metadata_json
        )
        db.session.add(new_item)
    cart = Cart.query.get(cart_id)
    if cart:
        cart.updated_at = datetime.utcnow()
    db.session.commit()
    return Cart.query.get(cart_id)


def get_item(cart_id, item_id):
    return CartItem.query.filter_by(id=item_id, cart_id=cart_id).first()


def remove_item(cart_id, item_id):
    item = get_item(cart_id, item_id)
    if not item:
        return None
    db.session.delete(item)
    cart = Cart.query.get(cart_id)
    if cart:
        cart.updated_at = datetime.utcnow()
    db.session.commit()
    return cart


def update_item_quantity(cart_id, item_id, quantity):
    item = get_item(cart_id, item_id)
    if not item:
        return None
    item.quantity = quantity
    item.updated_at = datetime.utcnow()
    cart = Cart.query.get(cart_id)
    if cart:
        cart.updated_at = datetime.utcnow()
    db.session.commit()
    return (cart, item)
