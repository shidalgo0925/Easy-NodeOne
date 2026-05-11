# Lógica del carrito (get_or_create, add_to_cart, resolve product para cart/add).
import hashlib

from app import Event, Service

from . import repository


def _membership_catalog_org_id(user):
    """Organización para resolver ``MembershipPlan`` (alinear con catálogo / tenant)."""
    from app import default_organization_id, _catalog_org_for_member_and_theme

    try:
        return int(getattr(user, 'organization_id', None) or _catalog_org_for_member_and_theme() or default_organization_id())
    except Exception:
        return int(default_organization_id())


def _membership_plan_for_cart(user, membership_type_slug: str):
    """Plan activo por slug y org, o None."""
    from app import MembershipPlan

    slug = (membership_type_slug or '').strip().lower()
    if not slug:
        return None
    oid = _membership_catalog_org_id(user)
    return MembershipPlan.query.filter_by(slug=slug, organization_id=oid, is_active=True).first()


def get_or_create_cart(user_id):
    """Obtener o crear carrito para el usuario (API usada por app y otros módulos)."""
    return repository.get_or_create_cart(user_id)


def add_to_cart(user_id, product_type, product_id, product_name, unit_price, quantity=1, product_description=None, metadata=None):
    """Agregar producto al carrito (API usada por app y otros módulos)."""
    cart = repository.get_or_create_cart(user_id)
    return repository.add_item(cart.id, product_type, product_id, product_name, unit_price, quantity, product_description, metadata)


# Diplomados IIUS: precios en centavos USD (un cargo por el total del plan; cuotas según política del instituto).
DIPLOMADOS_IIUS = {
    'neuro-liderazgo-intercultural': {
        'label': 'Neuro-Liderazgo y Coaching Ejecutivo Intercultural',
        'plans': {
            'full': (194900, 'Diplomado Neuro-Liderazgo — pago completo', 'Pago único USD 1,949 (20% dto. incl.)'),
            '6': (230000, 'Diplomado Neuro-Liderazgo — plan 6 cuotas', 'Total programa USD 2,300 (6 × USD 383). Un cargo hoy por el total.'),
            '10': (269000, 'Diplomado Neuro-Liderazgo — plan 10 cuotas', 'Total programa USD 2,690 (10 × USD 269). Un cargo hoy por el total.'),
        },
    },
    'neuro-descodificacion-psicogenealogia-pnl': {
        'label': 'Neuro-Descodificación™, Psicogenealogía y PNL',
        'plans': {
            'full': (194900, 'Diplomado Neuro-Descodificación — pago completo', 'Pago único USD 1,949 (20% dto. incl.)'),
            '6': (229900, 'Diplomado Neuro-Descodificación — plan 6 cuotas', 'Total programa USD 2,299 (6 × USD 383). Un cargo hoy por el total.'),
            '10': (269900, 'Diplomado Neuro-Descodificación — plan 10 cuotas', 'Total programa USD 2,699 (10 × USD 269). Un cargo hoy por el total.'),
        },
    },
    'neuro-teologia-coaching-cristiano-transgeneracional': {
        'label': 'Neuro-Teología y Coaching Cristiano Transgeneracional',
        'plans': {
            'full': (149900, 'Diplomado Neuro-Teología Cristiana — pago completo', 'Pago único USD 1,499 (20% dto. incl.)'),
            '6': (179900, 'Diplomado Neuro-Teología Cristiana — plan 6 cuotas', 'Total programa USD 1,799 (6 × USD 299). Un cargo hoy por el total.'),
            '10': (219900, 'Diplomado Neuro-Teología Cristiana — plan 10 cuotas', 'Total programa USD 2,199 (10 × USD 219). Un cargo hoy por el total.'),
        },
    },
    'neuro-heuristica-coaching-vida': {
        'label': 'Neuro-Heurística™ y Coaching de Vida',
        'plans': {
            'full': (149900, 'Diplomado Neuro-Heurística — pago completo', 'Pago único USD 1,499 (20% dto. incl.)'),
            '6': (179900, 'Diplomado Neuro-Heurística — plan 6 cuotas', 'Total programa USD 1,799 (6 × USD 299). Un cargo hoy por el total.'),
            '10': (219900, 'Diplomado Neuro-Heurística — plan 10 cuotas', 'Total programa USD 2,199 (10 × USD 219). Un cargo hoy por el total.'),
        },
    },
}

# Compat nombres antiguos
DIPLOMADO_NEURO_SLUG = 'neuro-liderazgo-intercultural'
DIPLOMADO_NEURO_PLANS = DIPLOMADOS_IIUS[DIPLOMADO_NEURO_SLUG]['plans']


def resolve_diplomado_plan(slug: str, plan_key: str):
    slug = (slug or '').strip().lower()
    plan_key = (plan_key or '').strip().lower()
    prog = DIPLOMADOS_IIUS.get(slug)
    if not prog:
        return None
    row = (prog.get('plans') or {}).get(plan_key)
    if not row:
        return None
    cents, name, desc = row
    pid = int(hashlib.md5(f'{slug}:{plan_key}'.encode()).hexdigest()[:8], 16) % 1000000
    meta = {'diplomado_slug': slug, 'plan': plan_key, 'currency': 'USD'}
    return pid, name, desc, float(cents), meta


def resolve_diplomado_neuro_plan(plan_key: str):
    """Compat: solo Neuro-Liderazgo."""
    return resolve_diplomado_plan(DIPLOMADO_NEURO_SLUG, plan_key)


def clear_diplomado_lines_from_cart(user_id):
    """Quita líneas de tipo diplomado (un programa a la vez en checkout)."""
    from app import CartItem, db

    cart = get_or_create_cart(user_id)
    CartItem.query.filter_by(cart_id=cart.id, product_type='diplomado').delete(synchronize_session=False)
    db.session.commit()


def clear_course_lines_from_cart(user_id):
    """Quita líneas de tipo course (una convocatoria a la vez en checkout)."""
    from app import CartItem, db

    cart = get_or_create_cart(user_id)
    CartItem.query.filter_by(cart_id=cart.id, product_type='course').delete(synchronize_session=False)
    db.session.commit()


def _resolve_course_cohort(user, service_id: int, cohort_id: int):
    """
    Valida programa COURSE + cohorte y devuelve (product_id, name, desc, cents, meta) o (None, mensaje).
    No escribe en el carrito.
    """
    from app import CourseCohort, default_organization_id, _catalog_org_for_member_and_theme

    if user is None:
        return None, 'Usuario no encontrado'
    oid = int(getattr(user, 'organization_id', None) or _catalog_org_for_member_and_theme() or default_organization_id())
    svc = Service.query.filter_by(id=int(service_id), organization_id=oid).first()
    if svc is None or (getattr(svc, 'service_type', None) or '').strip().upper() != 'COURSE':
        return None, 'Programa no disponible'
    ch = CourseCohort.query.filter_by(
        id=int(cohort_id), service_id=int(svc.id), organization_id=oid, is_active=True
    ).first()
    if ch is None:
        return None, 'Convocatoria no disponible'
    if ch.is_past_start():
        return None, 'Esta convocatoria ya no admite inscripciones.'
    avail = ch.spots_available()
    if avail is not None and avail <= 0:
        return None, 'No hay cupos disponibles para esta fecha.'

    active_membership = user.get_active_membership()
    membership_type = active_membership.membership_type if active_membership else 'basic'
    pricing = svc.pricing_for_membership(membership_type)
    if ch.price_override_cents is not None:
        cents = int(ch.price_override_cents)
    else:
        cents = int(round(float(pricing.get('final_price') or 0) * 100))

    label_part = (ch.label or '').strip() or (ch.start_date.isoformat() if ch.start_date else f'#{ch.id}')
    product_name = f'{svc.name} — {label_part}'
    desc = (svc.description or '').strip()[:2000] or f'Inscripción: {product_name}'
    meta = {
        'service_id': int(svc.id),
        'cohort_id': int(ch.id),
        'program_slug': (getattr(svc, 'program_slug', None) or '').strip(),
        'cohort_label': (ch.label or '').strip(),
        'modality': (ch.modality or '').strip(),
        'start_date': ch.start_date.isoformat() if ch.start_date else None,
        'membership_type': membership_type,
    }
    return (int(ch.id), product_name, desc, cents, meta), None


def add_course_cohort_to_cart(user_id: int, service_id: int, cohort_id: int):
    """
    Añade un programa (Service COURSE) + cohorte al carrito. Precio: override de cohorte o precio del servicio.
    Retorna (True, None) o (None, mensaje_error).
    """
    from app import User

    user = User.query.get(user_id)
    resolved, err = _resolve_course_cohort(user, service_id, cohort_id)
    if resolved is None:
        return None, err
    product_id, product_name, desc, cents, meta = resolved
    clear_course_lines_from_cart(user_id)
    add_to_cart(
        user_id,
        'course',
        product_id,
        product_name,
        float(cents),
        1,
        desc,
        meta,
    )
    return True, None


def add_diplomado_to_cart(user_id, slug: str, plan_key: str):
    """Añade un diplomado al carrito: primero ``AcademicProgram`` en BD, si no, IIUS (``DIPLOMADOS_IIUS``)."""
    from nodeone.modules.academic_enrollment import service as academic_enrollment_svc

    ok, err = academic_enrollment_svc.try_add_academic_program_to_cart(user_id, slug, plan_key)
    if ok is not None:
        if ok:
            return True, err
        return None, err
    resolved = resolve_diplomado_plan(slug, plan_key)
    if not resolved:
        return None, 'Plan o programa no válido'
    product_id, product_name, product_description, unit_price, metadata = resolved
    clear_diplomado_lines_from_cart(user_id)
    add_to_cart(
        user_id,
        'diplomado',
        product_id,
        product_name,
        unit_price,
        1,
        product_description,
        metadata,
    )
    return True, None


def add_diplomado_neuro_to_cart(user_id, plan_key: str):
    """Compat: Neuro-Liderazgo."""
    return add_diplomado_to_cart(user_id, DIPLOMADO_NEURO_SLUG, plan_key)


def resolve_product_for_cart(user, data):
    """
    Resuelve product_id, product_name, product_description, unit_price, metadata desde data (request).
    Retorna (product_id, product_name, product_description, unit_price, metadata) o (None, error_dict, status_code).
    """
    product_type = data.get('product_type')
    quantity = int(data.get('quantity', 1))

    if product_type == 'diplomado':
        slug = (data.get('diplomado_slug') or '').strip().lower()
        plan = (data.get('plan') or '').strip().lower()
        from nodeone.modules.academic_enrollment import service as academic_enrollment_svc

        oid = _membership_catalog_org_id(user)
        res_db = academic_enrollment_svc.resolve_pricing_for_cart(oid, slug, plan)
        if res_db:
            product_id, product_name, product_description, unit_price, metadata = res_db
            return (product_id, product_name, product_description, unit_price, metadata), None, None
        if slug not in DIPLOMADOS_IIUS:
            return None, {'success': False, 'error': 'Diplomado no disponible'}, 400
        resolved = resolve_diplomado_plan(slug, plan)
        if not resolved:
            return None, {'success': False, 'error': 'Plan no válido'}, 400
        product_id, product_name, product_description, unit_price, metadata = resolved
        return (product_id, product_name, product_description, unit_price, metadata), None, None

    if product_type == 'course':
        try:
            sid = int(data.get('service_id') or 0)
            cid = int(data.get('cohort_id') or 0)
        except (TypeError, ValueError):
            return None, {'success': False, 'error': 'Datos de programa inválidos'}, 400
        resolved, err = _resolve_course_cohort(user, sid, cid)
        if resolved is None:
            return None, {'success': False, 'error': err or 'No se pudo añadir al carrito'}, 400
        product_id, product_name, desc, cents, meta = resolved
        return (product_id, product_name, desc, float(cents), meta), None, None

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
        membership_type = (data.get('membership_type') or '').strip().lower()
        if not membership_type:
            return None, {'success': False, 'error': 'Tipo de membresía no especificado'}, 400
        plan = _membership_plan_for_cart(user, membership_type)
        if not plan:
            return None, {'success': False, 'error': 'Tipo de membresía no válido'}, 400
        yearly = float(plan.price_yearly or 0)
        unit_price = int(round(yearly * 100))
        product_name = f"Membresía {plan.name}"
        desc = (plan.description or '').strip()
        product_description = (desc[:2000] if desc else f"Plan anual — {plan.name}")
        metadata = {'membership_type': membership_type, 'membership_plan_id': plan.id}
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
        from app import _catalog_org_for_member_and_theme
        _oid = int(getattr(user, 'organization_id', None) or _catalog_org_for_member_and_theme())
        service = Service.query.filter_by(id=product_id, organization_id=_oid).first()
        if not service:
            return None, {'success': False, 'error': 'Servicio no encontrado'}, 404
        active_membership = user.get_active_membership()
        membership_type = active_membership.membership_type if active_membership else 'basic'
        pricing = service.pricing_for_membership(membership_type)
        final_price = pricing['final_price']
        unit_price = int(final_price * 100)
        product_name = service.name
        product_description = service.description or 'Servicio de Easy NodeOne'
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
    """Agrega membresía al carrito (checkout directo). Precio y validez desde ``MembershipPlan`` (BD)."""
    import hashlib

    from app import User

    user = User.query.get(user_id)
    if user is None:
        return None, 'membership'
    slug = (membership_type or '').strip().lower()
    plan = _membership_plan_for_cart(user, slug)
    if not plan:
        return None, 'membership'
    yearly = float(plan.price_yearly or 0)
    unit_cents = int(round(yearly * 100))
    product_id = int(hashlib.md5(slug.encode()).hexdigest()[:8], 16) % 1000000
    desc = (plan.description or '').strip()
    add_to_cart(
        user_id,
        'membership',
        product_id,
        f"Membresía {plan.name}",
        float(unit_cents),
        1,
        (desc[:2000] if desc else f"Plan anual — {plan.name}"),
        {'membership_type': slug, 'membership_plan_id': plan.id},
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
