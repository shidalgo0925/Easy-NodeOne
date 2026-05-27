#!/usr/bin/env python3
"""Smoke post-implementación: AcademicProgramResource (IIUS)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SMOKE_PREFIX = 'SMOKE_iius_resources_'


def main() -> int:
    from app import User, app, db
    from models.academic_program import AcademicProgram, AcademicProgramEnrollment, AcademicProgramResource
    from nodeone.modules.academic_enrollment.program_resources import (
        can_access_program_resource,
        validate_external_url,
        validate_local_resource_path,
    )
    from nodeone.modules.academic_enrollment.uploads import MAX_RESOURCE_BYTES, RESOURCE_EXTENSIONS

    failures: list[str] = []
    passed: list[str] = []

    def ok(msg: str):
        passed.append(msg)
        print(f'  OK  {msg}')

    def fail(msg: str):
        failures.append(msg)
        print(f' FAIL {msg}')

    with app.app_context():
        # --- Seguridad estática ---
        print('\n== Seguridad ==')
        for bad in ('javascript:alert(1)', 'file:///etc/passwd', 'data:text/html,x'):
            valid, _ = validate_external_url(bad)
            if valid:
                fail(f'external_url aceptó {bad!r}')
            else:
                ok(f'bloquea {bad.split(":")[0]}:')

        good, err = validate_external_url('https://example.com/doc.pdf')
        if good and not err:
            ok('acepta https válida')
        else:
            fail(f'https válida rechazada: {err}')

        if MAX_RESOURCE_BYTES == 25 * 1024 * 1024:
            ok('límite 25 MB confirmado')
        else:
            fail(f'límite inesperado: {MAX_RESOURCE_BYTES}')

        expected_ext = {'pdf', 'jpg', 'jpeg', 'png', 'webp', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
        if RESOURCE_EXTENSIONS == expected_ext:
            ok('extensiones permitidas confirmadas')
        else:
            fail(f'extensiones: {RESOURCE_EXTENSIONS}')

        program = AcademicProgram.query.filter_by(status='published', program_type='diplomado').first()
        if not program:
            fail('sin diplomado publicado para smoke')
            print('\n'.join(failures))
            return 1

        pdf_path = '/static/uploads/academic_programs/1/neuro_liderazgo_intercultural_program_pdf_fafad9f7aa08.pdf'
        fs, perr = validate_local_resource_path(pdf_path)
        if fs and not perr:
            ok('ruta PDF válida resuelve en disco')
        else:
            fail(f'PDF válido rechazado: {perr}')

        trav, terr = validate_local_resource_path('static/uploads/academic_programs/1/../../../../../etc/passwd')
        if trav is None and terr:
            ok('path traversal bloqueado')
        else:
            fail('path traversal NO bloqueado')

        # Limpiar recursos smoke previos
        AcademicProgramResource.query.filter(
            AcademicProgramResource.title.like(f'{SMOKE_PREFIX}%')
        ).delete(synchronize_session=False)
        db.session.commit()

        r_public = AcademicProgramResource(
            program_id=program.id,
            title=f'{SMOKE_PREFIX}public_pdf',
            resource_type='brochure',
            file_url=pdf_path,
            is_active=True,
            is_public=True,
            sort_order=1,
        )
        r_login = AcademicProgramResource(
            program_id=program.id,
            title=f'{SMOKE_PREFIX}login_pdf',
            resource_type='academic_program',
            file_url=pdf_path,
            is_active=True,
            is_public=False,
            requires_login=True,
            requires_purchase=False,
            sort_order=2,
        )
        r_purchase = AcademicProgramResource(
            program_id=program.id,
            title=f'{SMOKE_PREFIX}purchase_pdf',
            resource_type='bonus_material',
            file_url=pdf_path,
            is_active=True,
            is_public=False,
            requires_login=True,
            requires_purchase=True,
            sort_order=3,
        )
        r_inactive = AcademicProgramResource(
            program_id=program.id,
            title=f'{SMOKE_PREFIX}inactive_pdf',
            resource_type='other',
            file_url=pdf_path,
            is_active=False,
            is_public=True,
            sort_order=99,
        )
        db.session.add_all([r_public, r_login, r_purchase, r_inactive])
        db.session.commit()

        enrolled = (
            AcademicProgramEnrollment.query.filter_by(
                program_id=program.id, status='confirmed'
            ).first()
        )
        buyer = User.query.get(enrolled.user_id) if enrolled else None

        # Acceso lógico
        if can_access_program_resource(None, r_public, program):
            ok('público accesible anónimo (lógica)')
        else:
            fail('público NO accesible anónimo')

        if not can_access_program_resource(None, r_login, program):
            ok('requires_login bloquea anónimo (lógica)')
        else:
            fail('requires_login permite anónimo')

        if buyer and can_access_program_resource(buyer, r_purchase, program):
            ok('requires_purchase permite matriculado mismo program_id')
        else:
            fail('requires_purchase NO permite matriculado confirmado')

        other_prog = AcademicProgram.query.filter(
            AcademicProgram.status == 'published',
            AcademicProgram.id != program.id,
        ).first()
        if buyer and other_prog:
            fake = AcademicProgramResource(
                program_id=other_prog.id,
                title='fake',
                resource_type='other',
                file_url=pdf_path,
                is_active=True,
                requires_purchase=True,
            )
            if not can_access_program_resource(buyer, fake, other_prog):
                ok('requires_purchase exige matrícula del program_id correcto')
            else:
                fail('requires_purchase no valida program_id')

        client = app.test_client()
        slug = program.slug
        landing = client.get(f'/inscripcion/{slug}')
        if landing.status_code == 200:
            ok(f'landing /inscripcion/{slug} → 200')
        else:
            fail(f'landing status {landing.status_code}')

        html = landing.get_data(as_text=True)
        if 'Material descargable' in html:
            ok('bloque Material descargable visible')
        else:
            fail('bloque Material descargable ausente')

        if SMOKE_PREFIX + 'public_pdf' in html and SMOKE_PREFIX + 'login_pdf' in html:
            ok('recursos activos listados en landing')
        else:
            fail('recursos activos no listados')

        if SMOKE_PREFIX + 'inactive_pdf' not in html:
            ok('recurso inactivo no aparece en landing')
        else:
            fail('recurso inactivo visible en landing')

        # Descargas HTTP
        anon = client.get(f'/program-resources/{r_public.id}/download')
        if anon.status_code == 200:
            ok('descarga pública PDF sin login → 200')
        else:
            fail(f'descarga pública status {anon.status_code}')

        anon_login = client.get(f'/program-resources/{r_login.id}/download')
        if anon_login.status_code == 403:
            ok('requires_login anónimo → 403')
        else:
            fail(f'requires_login anónimo status {anon_login.status_code}')

        anon_buy = client.get(f'/program-resources/{r_purchase.id}/download')
        if anon_buy.status_code == 403:
            ok('requires_purchase anónimo → 403')
        else:
            fail(f'requires_purchase anónimo status {anon_buy.status_code}')

        if buyer:
            import subprocess

            backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            snippet = (
                'import sys\n'
                f"sys.path.insert(0, {backend!r})\n"
                'from app import app\n'
                'with app.app_context():\n'
                '    c = app.test_client()\n'
                f"    with c.session_transaction() as s:\n"
                f"        s['_user_id'] = {str(buyer.id)!r}\n"
                "        s['_fresh'] = True\n"
                f"    r = c.get('/program-resources/{r_purchase.id}/download')\n"
                '    print(r.status_code)\n'
            )
            proc = subprocess.run(
                [sys.executable, '-c', snippet],
                capture_output=True,
                text=True,
                cwd=backend,
                timeout=120,
            )
            code = (proc.stdout or '').strip().splitlines()[-1] if proc.stdout else ''
            if code == '200':
                ok('requires_purchase matriculado → 200 (subprocess)')
            else:
                fail(f'requires_purchase matriculado status {code or proc.stderr[:200]}')

        inactive_dl = client.get(f'/program-resources/{r_inactive.id}/download')
        if inactive_dl.status_code == 404:
            ok('recurso inactivo download → 404')
        else:
            fail(f'inactivo download status {inactive_dl.status_code}')

        # Admin protegido (sin sesión → redirect login)
        admin_client = app.test_client()
        with admin_client.session_transaction() as sess:
            sess.clear()
        admin_get = admin_client.get(
            f'/admin/academic-enrollment/programs/{program.id}/edit',
            follow_redirects=False,
        )
        admin_html = admin_get.get_data(as_text=True) if admin_get.status_code == 200 else ''
        if admin_get.status_code in (302, 401, 403):
            ok('admin edit sin login → bloqueado')
        elif admin_get.status_code == 200 and (
            'ap-form-page' in admin_html or 'Recursos del programa' in admin_html
        ):
            fail('admin edit sin login expone formulario')
        elif admin_get.status_code == 200:
            ok('admin edit sin login → página pública/login (200)')
        else:
            fail(f'admin edit sin login status {admin_get.status_code}')

        # external_url maliciosa en BD no debe servir
        r_bad = AcademicProgramResource(
            program_id=program.id,
            title=f'{SMOKE_PREFIX}bad_url',
            resource_type='external_link',
            external_url='javascript:alert(1)',
            is_active=True,
            is_public=True,
            sort_order=50,
        )
        db.session.add(r_bad)
        db.session.commit()
        bad_dl = client.get(f'/program-resources/{r_bad.id}/download')
        if bad_dl.status_code == 404:
            ok('javascript: en external_url → 404 al descargar')
        else:
            fail(f'javascript: external status {bad_dl.status_code}')

        # Limpieza smoke
        AcademicProgramResource.query.filter(
            AcademicProgramResource.title.like(f'{SMOKE_PREFIX}%')
        ).delete(synchronize_session=False)
        db.session.commit()
        ok('recursos smoke eliminados de BD')

    print(f'\nResumen: {len(passed)} OK, {len(failures)} FAIL')
    for f in failures:
        print(f'  - {f}')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
