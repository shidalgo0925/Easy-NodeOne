# Rutas del carrito y checkout.
import os

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


def _checkout_demo_hold_for_ui():
    """True = mostrar aviso de modo prueba (pagos demo en pending). Misma regla que payments_checkout._checkout_no_demo_auto_success."""
    if (os.environ.get('NODEONE_CHECKOUT_DEMO_AUTO_SUCCESS') or '').strip().lower() in ('1', 'true', 'yes', 'on'):
        return False
    if (os.environ.get('NODEONE_CHECKOUT_NO_DEMO_AUTO_SUCCESS') or '').strip().lower() in ('0', 'false', 'no', 'off'):
        return False
    return True


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
        from nodeone.modules.academic_enrollment.session_helpers import capture_utm_from_request

        capture_utm_from_request(request)
        pricing_plans = (
            AcademicProgramPricingPlan.query.filter_by(program_id=program.id, is_active=True)
            .order_by(AcademicProgramPricingPlan.sort_order.asc(), AcademicProgramPricingPlan.id.asc())
            .all()
        )
        no_active = not bool(pricing_plans)
        current_app.logger.warning('[academic_enrollment] plans_count=%s', len(pricing_plans))
        nav_prev = nav_next = None
        oid = int(program.organization_id)
        from nodeone.modules.academic_enrollment.catalog_public import adjacent_published_programs

        nav_prev, nav_next = adjacent_published_programs(oid, slug)
        from nodeone.modules.academic_enrollment.plan_display import plan_card_display
        from nodeone.modules.academic_enrollment.program_display_media import (
            enrollment_media_is_pdf,
            enrollment_media_path,
        )

        media_src = enrollment_media_path(program) or ''
        return render_template(
            'public/program_enrollment.html',
            program=program,
            pricing_plans=pricing_plans,
            plan_card_display=plan_card_display,
            diplomado_slug=slug,
            no_active_plans=no_active,
            nav_prev=nav_prev,
            nav_next=nav_next,
            media_src=media_src,
            media_is_pdf=enrollment_media_is_pdf(media_src),
        )
    from nodeone.modules.events.inscripcion_bridge import (
        find_event_for_inscripcion,
        is_event_inscripcion_slug,
        render_event_inscripcion_landing,
    )

    event = find_event_for_inscripcion(slug)
    if event is not None:
        current_app.logger.warning('[academic_enrollment] event_inscripcion slug=%s id=%s', slug, event.id)
        return render_event_inscripcion_landing(event)
    if is_event_inscripcion_slug(slug):
        from app import Event

        hidden = Event.query.filter_by(slug=slug).first()
        if hidden is not None:
            return render_template(
                'public/program_inscripcion_not_found.html',
                slug=slug,
                event_draft=(hidden.publish_status or '') != 'published',
            ), 404
    # Sin programa publicado en BD: no usar plantillas HTML legacy (un solo patrón program_enrollment).
    if slug in svc.DIPLOMADOS_IIUS:
        current_app.logger.warning(
            '[academic_enrollment] diplomado slug=%s sin AcademicProgram published; 404',
            slug,
        )
    return render_template('public/program_inscripcion_not_found.html', slug=slug), 404


@payments_bp.route('/inscripcion/<slug>/seleccionar-plan', methods=['POST'])
def inscripcion_seleccionar_plan(slug):
    """Guarda plan en sesión y envía a login/registro o al carrito si ya hay sesión."""
    from nodeone.modules.academic_enrollment import service as academic_enrollment_svc
    from nodeone.modules.academic_enrollment.session_helpers import set_pending_inscription

    slug = (slug or '').strip().lower()
    plan_code = (request.form.get('plan_code') or request.args.get('plan_code') or '').strip().lower()
    if not plan_code:
        flash('Elegí un plan de pago.', 'error')
        return redirect(url_for('payments.diplomado_landing', slug=slug))

    prog = academic_enrollment_svc.find_published_academic_program_for_inscripcion(slug)
    if prog is None and slug not in svc.DIPLOMADOS_IIUS:
        return render_template('public/program_inscripcion_not_found.html', slug=slug), 404

    if prog is not None:
        from app import AcademicProgramPricingPlan

        plan_row = AcademicProgramPricingPlan.query.filter_by(
            program_id=prog.id, code=plan_code, is_active=True
        ).first()
        if plan_row is None:
            flash('Plan no disponible.', 'error')
            return redirect(url_for('payments.diplomado_landing', slug=slug))
        set_pending_inscription(slug, plan_code, int(prog.organization_id))
    else:
        set_pending_inscription(slug, plan_code)

    if current_user.is_authenticated:
        return redirect(url_for('payments.diplomado_continuar', slug=slug, plan=plan_code))

    dest = url_for('payments.diplomado_continuar', slug=slug, plan=plan_code)
    if request.form.get('flow') == 'register':
        return redirect(url_for('register', next=dest))
    return redirect(url_for('auth.login', next=dest))


@payments_bp.route('/inscripcion/<slug>/continuar/<plan>')
@login_required
def diplomado_continuar(slug, plan):
    """Añade el diplomado al carrito y envía al checkout (requiere sesión y email verificado en /checkout)."""
    from nodeone.modules.academic_enrollment.session_helpers import clear_pending_inscription

    clear_pending_inscription()
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
        from nodeone.modules.academic_enrollment.session_helpers import set_pending_inscription

        set_pending_inscription(
            slug,
            plan_code,
            int(prog.organization_id),
            return_url=url_for('payments.checkout_programa_shortcut', slug=slug, plan_code=plan_code),
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
        from app import PAYMENT_PROCESSORS_AVAILABLE, STRIPE_PUBLISHABLE_KEY, PaymentConfig
        from nodeone.services import organization_payment_methods as opm
        from utils.organization import resolve_current_organization

        pay_oid = int(resolve_current_organization())
        pcfg = PaymentConfig.get_active_config(organization_id=pay_oid)
        ctx = opm.build_checkout_payment_context(pay_oid, payment_config=pcfg)
        stripe_pk = STRIPE_PUBLISHABLE_KEY
        if not PAYMENT_PROCESSORS_AVAILABLE:
            pm = dict(ctx['payment_methods'])
            ctx['payment_methods'] = pm
            ctx['checkout_method_order'] = [k for k in ctx.get('checkout_method_order', []) if k in pm]
            ctx['method_rows'] = [r for r in ctx.get('method_rows', []) if r.get('method_key') in pm]
            ctx['checkout_first_method'] = ctx.get('checkout_first_method') or (
                ctx['checkout_method_order'][0] if ctx.get('checkout_method_order') else None
            )
    except Exception:
        from payment_processors import INTL_WIRE_DEFAULTS

        try:
            from app import db

            db.session.rollback()
        except Exception:
            pass
        ctx = {
            'payment_methods': {'paypal': 'PayPal'},
            'method_rows': [],
            'method_by_key': {},
            'checkout_method_order': ['paypal'],
            'checkout_first_method': 'paypal',
            'checkout_has_immediate': True,
            'checkout_has_manual_validation': False,
            'checkout_other_method_keys': [],
            'intl_wire_display': dict(INTL_WIRE_DEFAULTS),
            'yappy_checkout': None,
        }
        stripe_pk = None

    return render_template(
        'checkout.html',
        cart=cart,
        total_amount=total_amount,
        discount_breakdown=discount_breakdown,
        stripe_publishable_key=stripe_pk,
        payment_methods=ctx['payment_methods'],
        intl_wire_display=ctx['intl_wire_display'],
        yappy_checkout=ctx['yappy_checkout'],
        checkout_first_method=ctx['checkout_first_method'],
        checkout_has_immediate=ctx['checkout_has_immediate'],
        checkout_has_manual_validation=ctx['checkout_has_manual_validation'],
        checkout_other_method_keys=ctx['checkout_other_method_keys'],
        checkout_method_order=ctx.get('checkout_method_order', []),
        method_by_key=ctx.get('method_by_key', {}),
        checkout_demo_hold=_checkout_demo_hold_for_ui(),
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
