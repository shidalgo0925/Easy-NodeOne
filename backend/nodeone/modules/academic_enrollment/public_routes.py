"""API y vitrina HTML del catálogo de inscripción (PASO 3 IIUS)."""

from __future__ import annotations


def register_academic_enrollment_public_routes(app):
    from flask import abort, jsonify, make_response, render_template, request

    _vfs = getattr(app, 'view_functions', {})

    def _cors(resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    if 'public_academic_programs_api' not in _vfs:

        @app.route('/api/public/academic-programs', methods=['GET', 'OPTIONS'])
        def public_academic_programs_api():
            if request.method == 'OPTIONS':
                return _cors(make_response('', 204))
            from nodeone.modules.academic_enrollment.catalog_public import (
                list_published_programs_payload,
                resolve_catalog_organization_id,
            )

            oid = resolve_catalog_organization_id()
            if oid is None:
                return _cors(jsonify({'ok': False, 'error': 'organization_unknown'})), 400
            payload = list_published_programs_payload(oid)
            category = (request.args.get('category') or '').strip()
            if category:
                filtered = [p for p in payload['programs'] if (p.get('category') or '') == category]
                payload = {
                    **payload,
                    'programs': filtered,
                    'by_category': {category: filtered} if filtered else {},
                    'categories': [category] if filtered else [],
                    'count': len(filtered),
                }
            return _cors(jsonify({'ok': True, **payload}))

    if 'public_diplomado_inicios_api' not in _vfs:

        @app.route('/api/public/diplomado-inicios', methods=['GET', 'OPTIONS'])
        def public_diplomado_inicios_api():
            """Fechas y títulos de diplomados publicados (calendario WP coaching)."""
            if request.method == 'OPTIONS':
                return _cors(make_response('', 204))
            from nodeone.modules.academic_enrollment.catalog_public import resolve_catalog_organization_id
            from nodeone.modules.academic_enrollment.diplomado_inicios_public import list_diplomado_inicios_payload

            oid = resolve_catalog_organization_id()
            if oid is None:
                return _cors(jsonify({'ok': False, 'error': 'organization_unknown'})), 400
            payload = list_diplomado_inicios_payload(oid)
            return _cors(jsonify(payload))

    if 'public_academic_programs_catalog' not in _vfs:

        @app.route('/programas', methods=['GET'])
        def public_academic_programs_catalog():
            from nodeone.modules.academic_enrollment.catalog_public import (
                catalog_can_manage_programs,
                distinct_program_categories,
                group_programs_for_template,
                resolve_catalog_organization_id,
            )

            oid = resolve_catalog_organization_id()
            if oid is None:
                abort(404)
            q = (request.args.get('q') or '').strip()
            category = (request.args.get('category') or 'all').strip()
            program_type = (request.args.get('program_type') or 'all').strip()
            sections = group_programs_for_template(
                oid, q=q, category=category, program_type=program_type
            )
            has_filters = bool(q) or category not in ('', 'all') or program_type not in ('', 'all')
            if not sections and not has_filters:
                abort(404)
            can_manage = catalog_can_manage_programs()
            return render_template(
                'public/academic_programs_catalog.html',
                sections=sections,
                organization_id=oid,
                catalog_can_manage=can_manage,
                filter_q=q,
                filter_category=category,
                filter_program_type=program_type,
                filter_categories=distinct_program_categories(oid, published_only=True),
                program_types=('curso', 'diplomado', 'taller', 'certificacion', 'servicio', 'programa'),
            )

    if 'academic_program_public_pdf' not in _vfs:

        @app.route('/programa-academico/<slug>/pdf', methods=['GET'])
        def academic_program_public_pdf(slug):
            """URL estable para landings externos: abre el PDF del diplomado (público, inline)."""
            from flask import abort

            from nodeone.modules.academic_enrollment.catalog_public import resolve_catalog_organization_id
            from nodeone.modules.academic_enrollment.program_academic_pdf import (
                find_program_for_public_pdf,
                serve_academic_program_pdf,
            )

            slug = (slug or '').strip().lower()
            oid = resolve_catalog_organization_id()
            program = find_program_for_public_pdf(slug, oid)
            if program is None:
                abort(404)
            resp = serve_academic_program_pdf(program)
            if resp is None:
                abort(404)
            return resp

    if 'academic_program_pdf_lead_form' not in _vfs:

        @app.route('/programa-academico/<slug>/solicitar-pdf', methods=['GET'])
        @app.route('/programa-academico/<slug>/lead-capture-v2', methods=['GET'])
        def academic_program_pdf_lead_form(slug):
            """Formulario lead_capture_v2: captura datos antes de abrir el PDF (pruebas / enlace desde WP)."""
            from flask import abort, render_template

            from nodeone.modules.academic_enrollment.catalog_public import resolve_catalog_organization_id
            from nodeone.modules.academic_enrollment.program_academic_pdf import (
                find_program_for_public_pdf,
                program_has_public_academic_pdf,
            )

            slug = (slug or '').strip().lower()
            oid = resolve_catalog_organization_id()
            program = find_program_for_public_pdf(slug, oid)
            if program is None or not program_has_public_academic_pdf(program):
                abort(404)
            source = (request.args.get('source') or 'wp_landing_pdf').strip()[:120] or 'wp_landing_pdf'
            embed = (request.args.get('embed') or '').strip().lower() in ('1', 'true', 'yes')
            return render_template(
                'public/academic_program_pdf_lead_form.html',
                program=program,
                source=source,
                embed=embed,
            )

    if 'academic_program_pdf_confirm' not in _vfs:

        @app.route('/programa-academico/<slug>/confirmar-pdf', methods=['GET'])
        def academic_program_pdf_confirm(slug):
            """Confirma el correo del lead y redirige al PDF."""
            from flask import abort, redirect, render_template

            from nodeone.modules.academic_enrollment.catalog_public import resolve_catalog_organization_id
            from nodeone.modules.academic_enrollment.pdf_lead_confirmation import (
                confirm_lead_by_token,
                pdf_download_url,
            )
            from nodeone.modules.academic_enrollment.program_academic_pdf import (
                find_program_for_public_pdf,
                program_has_public_academic_pdf,
            )

            slug = (slug or '').strip().lower()
            token = (request.args.get('token') or '').strip()
            if not token:
                abort(400)

            lead, program, err = confirm_lead_by_token(program_slug=slug, token=token)
            oid = resolve_catalog_organization_id()

            if err == 'token_not_found':
                abort(404)
            if err == 'token_expired':
                return render_template(
                    'public/academic_program_pdf_confirm.html',
                    state='expired',
                    program_slug=slug,
                    program_name=None,
                ), 410
            if err in ('program_mismatch', 'invalid_status', 'invalid_request'):
                abort(400)
            if program is None:
                program = find_program_for_public_pdf(slug, oid)
            if program is None or not program_has_public_academic_pdf(program):
                abort(404)

            base = request.host_url.rstrip('/')
            pdf_url = pdf_download_url(base_url=base, program_slug=slug)

            if request.args.get('preview') == '1':
                return render_template(
                    'public/academic_program_pdf_confirm.html',
                    state='success',
                    program_slug=slug,
                    program_name=program.name,
                    pdf_url=pdf_url,
                )

            return redirect(pdf_url, code=302)

    if 'program_resource_download' not in _vfs:

        @app.route('/program-resources/<int:resource_id>/download', methods=['GET'])
        def program_resource_download(resource_id):
            from flask import abort

            from nodeone.modules.academic_enrollment.program_resources import (
                find_resource_for_download,
                serve_program_resource,
            )

            resource, program = find_resource_for_download(resource_id)
            if resource is None:
                abort(404)
            resp, err = serve_program_resource(resource, program)
            if err == 'forbidden':
                abort(403)
            if resp is None:
                abort(404)
            return resp
