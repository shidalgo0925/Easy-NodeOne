"""Rutas post-pago: agendar coaching (V1)."""

from __future__ import annotations


def register_academic_enrollment_agenda_routes(app):
    from flask import abort, jsonify, redirect, render_template, request, url_for
    from flask_login import current_user, login_required

    if 'academic_enrollment_agenda_page' in getattr(app, 'view_functions', {}):
        return

    @app.route('/inscripcion/agendar/<int:enrollment_id>', methods=['GET'])
    @login_required
    def academic_enrollment_agenda_page(enrollment_id):
        from models.academic_program import AcademicProgramEnrollment
        from nodeone.modules.academic_enrollment.agenda import (
            enrollment_agenda_display,
            enrollment_needs_agenda,
        )
        from nodeone.modules.ecalendar.services.config import load_ecalendar_config
        from nodeone.modules.ecalendar.services.google_calendar import oauth_valid

        en = AcademicProgramEnrollment.query.get_or_404(int(enrollment_id))
        if en.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
            abort(403)
        if not en.program:
            abort(404)

        if (en.agenda_status or '').strip().lower() == 'scheduled' and en.scheduled_at:
            return render_template(
                'public/program_enrollment_agenda_done.html',
                enrollment=en,
                scheduled_at=en.scheduled_at,
            )

        if not enrollment_needs_agenda(en):
            return redirect(url_for('payments.program_enrollment_thanks', enrollment_id=en.id))

        cfg = load_ecalendar_config(organization_id=int(en.organization_id))
        calendar_ok = cfg.enabled and cfg.google_configured and oauth_valid(cfg)
        return render_template(
            'public/program_enrollment_agenda.html',
            enrollment=en,
            program=en.program,
            calendar_ok=calendar_ok,
            timezone=cfg.timezone,
            horizon_days=cfg.horizon_days,
        )

    @app.route('/inscripcion/agendar/<int:enrollment_id>', methods=['POST'])
    @login_required
    def academic_enrollment_agenda_confirm(enrollment_id):
        from models.academic_program import AcademicProgramEnrollment
        from nodeone.modules.academic_enrollment.agenda import book_enrollment_agenda, enrollment_needs_agenda

        en = AcademicProgramEnrollment.query.get_or_404(int(enrollment_id))
        if en.user_id != current_user.id and not getattr(current_user, 'is_admin', False):
            abort(403)
        if not enrollment_needs_agenda(en):
            return jsonify({'ok': False, 'error': 'agenda_not_pending'}), 400

        data = request.get_json(silent=True) or {}
        slot_start = (data.get('slot_start') or request.form.get('slot_start') or '').strip()
        if not slot_start:
            return jsonify({'ok': False, 'error': 'invalid_slot_start'}), 400

        result, status, err = book_enrollment_agenda(en, slot_start)
        if err:
            return jsonify({'ok': False, 'error': err}), status
        return jsonify(result), status
