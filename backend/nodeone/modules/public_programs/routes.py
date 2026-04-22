"""API pública y landing HTML de programas / cohortes."""

from __future__ import annotations


def _build_public_program_payload(M, program_slug: str):
    """
    Datos compartidos por GET /api/public/programs/<slug>/cohorts y GET /programs/<slug>.
    Retorna (payload, None) o (None, código_error).
    """
    from datetime import date

    slug = (program_slug or '').strip().lower()
    if not slug:
        return None, 'invalid_slug'

    from utils.organization import resolve_current_organization

    oid = resolve_current_organization()
    if oid is None:
        return None, 'organization_unknown'

    svc = (
        M.Service.query.filter_by(organization_id=int(oid), program_slug=slug, is_active=True)
        .filter(M.Service.service_type == 'COURSE')
        .first()
    )
    if svc is None:
        return None, 'program_not_found'

    today = date.today()
    q = (
        M.CourseCohort.query.filter_by(
            organization_id=int(oid),
            service_id=int(svc.id),
            is_active=True,
        )
        .filter((M.CourseCohort.start_date.is_(None)) | (M.CourseCohort.start_date >= today))
        .order_by(M.CourseCohort.display_order, M.CourseCohort.start_date, M.CourseCohort.id)
    )
    rows = q.all()

    out_cohorts = []
    for c in rows:
        if c.is_past_start():
            continue
        avail = c.spots_available()
        out_cohorts.append(
            {
                'id': c.id,
                'slug': (c.slug or '').strip() or None,
                'label': (c.label or '').strip() or None,
                'start_date': c.start_date.isoformat() if c.start_date else None,
                'end_date': c.end_date.isoformat() if c.end_date else None,
                'weeks_duration': c.weeks_duration,
                'modality': (c.modality or 'virtual').strip().lower(),
                'spots_total': int(c.capacity_total or 0) or None,
                'spots_available': avail,
                'price_cents': int(c.price_override_cents)
                if c.price_override_cents is not None
                else None,
                'checkout_url_template': '/checkout/course?service_id={service_id}&cohort_id={cohort_id}'.format(
                    service_id=svc.id, cohort_id=c.id
                ),
            }
        )

    from flask import request

    base = (request.url_root or '').rstrip('/')
    registration_only = bool(out_cohorts) and all(not oc.get('start_date') for oc in out_cohorts)
    payload = {
        'organization_id': int(oid),
        'program': {
            'id': svc.id,
            'name': svc.name or '',
            'slug': slug,
            'description': (svc.description or '')[:4000],
            'base_price': float(svc.base_price or 0),
            'currency': 'USD',
        },
        'cohorts': out_cohorts,
        'checkout_base_url': base,
        'registration_only': registration_only,
    }
    return payload, None


def register_public_program_api_routes(app):
    from flask import abort, jsonify, make_response, render_template, request

    import app as M

    def _cors(resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    if 'public_program_cohorts' not in getattr(app, 'view_functions', {}):

        @app.route('/api/public/programs/<program_slug>/cohorts', methods=['GET', 'OPTIONS'])
        def public_program_cohorts(program_slug):
            if request.method == 'OPTIONS':
                return _cors(make_response('', 204))
            payload, err = _build_public_program_payload(M, program_slug)
            if err == 'invalid_slug':
                return _cors(jsonify({'error': 'invalid_slug'})), 400
            if err == 'organization_unknown':
                return _cors(jsonify({'error': 'organization_unknown'})), 400
            if err == 'program_not_found':
                return _cors(jsonify({'error': 'program_not_found'})), 404
            return _cors(jsonify(payload))

    if 'public_program_landing' not in getattr(app, 'view_functions', {}):

        @app.route('/programs/<program_slug>', methods=['GET'])
        def public_program_landing(program_slug):
            payload, err = _build_public_program_payload(M, program_slug)
            if err == 'invalid_slug':
                abort(400)
            if err in ('organization_unknown', 'program_not_found'):
                abort(404)
            return render_template('public/program_cohorts_landing.html', payload=payload)
