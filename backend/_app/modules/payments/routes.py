# Rutas del carrito y checkout.
from flask import Blueprint, current_app, request, jsonify, render_template, redirect, url_for, abort, session
from flask_login import login_required, current_user

from app import email_verified_required, flash
from . import service as svc

payments_bp = Blueprint('payments', __name__, url_prefix='')

# Slug → plantilla de landing (debe coincidir con claves de ``DIPLOMADOS_IIUS`` en service).
DIPLOMADO_LANDING_TEMPLATES = {
    'neuro-liderazgo-intercultural': 'public/inscription_neuro_liderazgo.html',
    'neuro-descodificacion-psicogenealogia-pnl': 'public/inscription_neuro_descodificacion.html',
    'neuro-teologia-coaching-cristiano-transgeneracional': 'public/inscription_neuro_teologia_cristiana.html',
    'neuro-heuristica-coaching-vida': 'public/inscription_neuro_heuristica.html',
}


def _inscripcion_get_org_from_request():
    """SaaS org asociada al host (mismo criterio que catálogo; sin sesión forzada en anónimos)."""
    from app import SaasOrganization, _organization_id_from_request_host

    oid = _organization_id_from_request_host(request)
    if oid is None:
        return None
    return SaasOrganization.query.get(int(oid))


@payments_bp.route('/inscripcion/<slug>')
def diplomado_landing(slug):
    """Cursos: AcademicProgram (BD) por tenant; IIUS: legacy con plantillas fijas."""
    from app import AcademicProgramPricingPlan
    from nodeone.modules.academic_enrollment import service as academic_enrollment_svc

    slug = (slug or '').strip().lower()
    org = _inscripcion_get_org_from_request()
    current_app.logger.warning(
        '[academic_enrollment] inscripcion_landing host=%s org_id=%s slug=%s',
        (request.host or '')[:200],
        getattr(org, 'id', None) if org else None,
        slug,
    )
    program = academic_enrollment_svc.find_published_academic_program_for_inscripcion(slug)
    current_app.logger.warning(
        '[academic_enrollment] program_id=%s',
        getattr(program, 'id', None) if program else None,
    )
    if program is not None:
        pricing_plans = (
            AcademicProgramPricingPlan.query.filter_by(program_id=program.id, is_active=True)
            .order_by(AcademicProgramPricingPlan.sort_order.asc(), AcademicProgramPricingPlan.id.asc())
            .all()
        )
        no_active = not bool(pricing_plans)
        current_app.logger.warning('[academic_enrollment] plans_count=%s', len(pricing_plans))
        return render_template(
            'public/program_enrollment.html',
            program=program,
            pricing_plans=pricing_plans,
            diplomado_slug=slug,
            no_active_plans=no_active,
        )
    if slug in svc.DIPLOMADOS_IIUS:
        tpl = DIPLOMADO_LANDING_TEMPLATES.get(slug)
        if tpl:
            return render_template(tpl, diplomado_slug=slug)
    abort(404)


@payments_bp.route('/inscripcion/<slug>/continuar/<plan>')
@login_required
def diplomado_continuar(slug, plan):
    """Añade el diplomado al carrito y envía al checkout (requiere sesión y email verificado en /checkout)."""
    from nodeone.modules.academic_enrollment import service as academic_enrollment_svc

    slug = (slug or '').strip().lower()
    ok, err = svc.add_diplomado_to_cart(current_user.id, slug, plan)
    if not ok:
        flash(err or 'No se pudo preparar el pago.', 'error')
        if (
            academic_enrollment_svc.find_published_academic_program_for_inscripcion(slug)
            or slug in svc.DIPLOMADOS_IIUS
        ):
            return redirect(url_for('payments.diplomado_landing', slug=slug))
        return redirect(url_for('services.list'))
    flash('Plan añadido al carrito. Completa el pago en el siguiente paso.', 'success')
    return redirect(url_for('payments.checkout'))


@payments_bp.route('/checkout/programa/<slug>/<plan_code>')
def checkout_programa_shortcut(slug, plan_code):
    """Alias: mismo flujo que continuar (login → carrito → checkout)."""
    from nodeone.modules.academic_enrollment import service as academic_enrollment_svc

    slug = (slug or '').strip().lower()
    plan_code = (plan_code or '').strip().lower()
    prog = academic_enrollment_svc.find_published_academic_program_for_inscripcion(slug)
    if prog is not None:
        session['pending_program_slug'] = slug
        session['pending_plan_code'] = plan_code
        session['pending_organization_id'] = int(prog.organization_id)
        session['pending_return_url'] = url_for(
            'payments.checkout_programa_shortcut', slug=slug, plan_code=plan_code
        )
    if not current_user.is_authenticated:
        return redirect(
            url_for('auth.login', next=url_for('payments.diplomado_continuar', slug=slug, plan=plan_code))
        )
    return redirect(url_for('payments.diplomado_continuar', slug=slug, plan=plan_code))


@payments_bp.route('/inscripcion/gracias/<int:enrollment_id>')
@login_required
def program_enrollment_thanks(enrollment_id):
    from app import AcademicProgramEnrollment

    en = AcademicProgramEnrollment.query.get_or_404(enrollment_id)
    if en.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
        abort(403)
    return render_template('public/program_enrollment_thanks.html', enrollment=en)


@payments_bp.route('/checkout/course')
@login_required
def checkout_course():
    """Inscripción a una cohorte concreta (desde landing). Query: service_id, cohort_id."""
    try:
        sid = int(request.args.get('service_id', 0))
        cid = int(request.args.get('cohort_id', 0))
    except (TypeError, ValueError):
        flash('Enlace de inscripción no válido.', 'error')
        return redirect(url_for('services.list'))
    ok, err = svc.add_course_cohort_to_cart(current_user.id, sid, cid)
    if not ok:
        flash(err or 'No se pudo preparar la inscripción.', 'error')
        return redirect(url_for('services.list'))
    flash('Inscripción añadida al carrito. Completa el pago en el siguiente paso.', 'success')
    return redirect(url_for('payments.checkout'))


@payments_bp.route('/cart')
@login_required
def cart():
    cart = svc.get_or_create_cart(current_user.id)
    return render_template('cart.html', cart=cart)


@payments_bp.route('/cart/add', methods=['POST'])
@login_required
@email_verified_required
def cart_add():
    """Precio y nombre: siempre vía ``resolve_product_for_cart`` (servidor); no confiar en base_price del cliente."""
    try:
        data = request.get_json() if request.is_json else request.form
        product_type = data.get('product_type')
        quantity = int(data.get('quantity', 1))
        resolved, err, status = svc.resolve_product_for_cart(current_user, data)
        if err is not None:
            return jsonify(err), status
        product_id, product_name, product_description, unit_price, metadata = resolved
        cart = svc.add_to_cart(
            current_user.id,
            product_type,
            product_id,
            product_name,
            unit_price,
            quantity,
            product_description,
            metadata,
        )
        return jsonify({
            'success': True,
            'message': 'Producto agregado al carrito',
            'cart_items_count': cart.get_items_count(),
            'cart_total': cart.get_total()
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Error de validación: {str(e)}'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    try:
        cart_after, err = svc.remove_item(current_user.id, item_id)
        if err is not None:
            return jsonify(err), 404
        return jsonify({
            'success': True,
            'message': 'Producto eliminado del carrito',
            'cart_items_count': cart_after.get_items_count(),
            'cart_total': cart_after.get_total()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
    try:
        data = request.get_json() if request.is_json else request.form
        quantity = int(data.get('quantity', 1))
        cart_after, item, err, status = svc.update_item(current_user.id, item_id, quantity)
        if err is not None:
            return jsonify(err), status
        if cart_after is None:
            return jsonify({'success': False, 'error': 'Item no encontrado'}), 404
        return jsonify({
            'success': True,
            'message': 'Cantidad actualizada',
            'cart_items_count': cart_after.get_items_count(),
            'cart_total': cart_after.get_total(),
            'item_subtotal': item.get_subtotal()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/cart/count', methods=['GET'])
@login_required
def cart_count():
    try:
        cart = svc.get_or_create_cart(current_user.id)
        return jsonify({
            'count': cart.get_items_count(),
            'total': cart.get_total()
        })
    except Exception:
        return jsonify({'count': 0, 'total': 0})


@payments_bp.route('/checkout')
@login_required
@email_verified_required
def checkout():
    data = svc.get_checkout_data(current_user.id)
    if data[0] is None:
        flash('Tu carrito está vacío. Agrega productos antes de proceder al pago.', 'warning')
        return redirect(url_for(data[1]))
    cart, total_amount, discount_breakdown = data
    try:
        from app import PAYMENT_METHODS, PAYMENT_PROCESSORS_AVAILABLE, STRIPE_PUBLISHABLE_KEY
        payment_methods = PAYMENT_METHODS if PAYMENT_PROCESSORS_AVAILABLE else {'stripe': 'Stripe (Tarjeta de Crédito)'}
        stripe_pk = STRIPE_PUBLISHABLE_KEY
    except Exception:
        payment_methods = {'stripe': 'Stripe (Tarjeta de Crédito)'}
        stripe_pk = None
    return render_template(
        'checkout.html',
        cart=cart,
        total_amount=total_amount,
        discount_breakdown=discount_breakdown,
        stripe_publishable_key=stripe_pk,
        payment_methods=payment_methods,
    )


@payments_bp.route('/checkout/<membership_type>')
@login_required
def checkout_membership(membership_type):
    redirect_ok, redirect_err = svc.add_membership_to_cart_and_checkout(current_user.id, membership_type)
    if redirect_err:
        flash('Tipo de membresía inválido.', 'error')
        return redirect(url_for(redirect_err))
    return redirect(url_for(redirect_ok))


@payments_bp.route('/api/cart/apply-discount-code', methods=['POST'])
@login_required
def api_apply_discount_code():
    try:
        data = request.get_json() or {}
        code = data.get('code', '').strip().upper()
        success, message, breakdown = svc.apply_discount_code(current_user.id, code)
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'breakdown': breakdown
            })
        return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payments_bp.route('/api/cart/remove-discount-code', methods=['POST'])
@login_required
def api_remove_discount_code():
    try:
        breakdown = svc.remove_discount_code(current_user.id)
        return jsonify({
            'success': True,
            'message': 'Código de descuento removido',
            'breakdown': breakdown
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
