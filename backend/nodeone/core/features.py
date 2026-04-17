"""Registro modular de blueprints / flags SaaS."""

import os

# Nota: Flask 3+ no permite register_blueprint durante/tras el primer request;
# diferir citas con before_request rompe el arranque. Para bajar RAM: partir app.py/routes
# o workers que no importen el monolito completo.
#
# NODEONE_SKIP_APPOINTMENTS_MODULE=1 — no registrar citas.
# NODEONE_SKIP_EVENTS_MODULE=1 — no registrar eventos.
# NODEONE_SKIP_CERTIFICATES_MODULE=1 — no registrar certificados.
# NODEONE_SKIP_MARKETING_MODULE=1 — no registrar marketing.
# NODEONE_SKIP_SAAS_ADMIN_API=1 — no registrar /api/admin/saas.
# NODEONE_SKIP_AUTH_BLUEPRINT=1 — no registrar auth (_app).
# NODEONE_SKIP_MEMBERS_PACK=1 — no registrar members/communications/services/integrations.
# NODEONE_SKIP_POLICIES_BLUEPRINT=1 — no registrar policies.
# NODEONE_SKIP_PAYMENTS_BLUEPRINT=1 — no registrar payments (blueprint _app).
# NODEONE_SKIP_PAYMENTS_CHECKOUT_BLUEPRINT=1 — no registrar checkout/webhook (payments_checkout).
# NODEONE_SKIP_PAYMENTS_ADMIN_BLUEPRINT=1 — no registrar admin pagos /api/admin/payments/* (payments_admin).
# NODEONE_SKIP_USER_API_BLUEPRINT=1 — no registrar /api/user (nodeone.modules.user_api).
# NODEONE_SKIP_MEMBER_HISTORY_API_BLUEPRINT=1 — no registrar /api/history (miembro).
# NODEONE_SKIP_ADMIN_HISTORY_API_BLUEPRINT=1 — no registrar /api/admin/history.
# NODEONE_SKIP_PUBLIC_API_BLUEPRINT=1 — no registrar onboarding/demo público.
# NODEONE_SKIP_AI_API_BLUEPRINT=1 — no registrar /api/ai/ping ni /api/admin/ai/*.
# NODEONE_SKIP_OFFICE365_ADMIN_BLUEPRINT=1 — no registrar /admin/office365/* (sin afectar /office365 miembro).
# NODEONE_OFFICE365_MODULE_ENABLED=0 — apaga todo el despliegue O365 (sin tocar el toggle por tenant en Admin → Módulos).
# NODEONE_SKIP_ADMIN_EMAIL_API_BLUEPRINT=1 — no registrar /api/admin/email/*.
# NODEONE_SKIP_MEDIA_ADMIN_BLUEPRINT=1 — no registrar /admin/media ni /api/*/media/*.
# NODEONE_SKIP_ADMIN_EXPORT_BLUEPRINT=1 — no registrar /admin/export ni /api/admin/export/*.
# NODEONE_SKIP_ADMIN_BACKUP_BLUEPRINT=1 — no registrar /admin/backup*.
# NODEONE_SKIP_ADMIN_DISCOUNT_CODES_BLUEPRINT=1 — no registrar /admin/discount-codes* ni /api/admin/discount-codes/*.
# NODEONE_SKIP_ADMIN_MEMBERSHIP_DISCOUNTS_BLUEPRINT=1 — no registrar membership-discounts ni /admin/master-discount.
# NODEONE_SKIP_MEMBER_COMMUNITY_BLUEPRINT=1 — no registrar /foros ni /grupos.
# NODEONE_SKIP_MEMBER_PAGES_BLUEPRINT=1 — no registrar /settings ni /help.
# NODEONE_SKIP_ADMIN_SERVICES_CATALOG_BLUEPRINT=1 — no registrar /admin/services* ni /admin/service-categories* (catálogo).
# NODEONE_SKIP_ANALYTICS_MODULE=1 — no registrar /admin/analytics* ni /api/admin/analytics/* (KPIs / tableros).
# NODEONE_SKIP_CRM_API_BLUEPRINT=1 — no registrar /crm/* (leads, stages, activities, reportes).
# NODEONE_SKIP_ADMIN_SALES_ACCOUNTING_ROUTES=1 — no registrar /admin/sales/quotations ni /admin/accounting/invoices.
# NODEONE_SKIP_WORKSHOP_MODULE=1 — no registrar /api/workshop ni /admin/workshop (taller / recepción).
# NODEONE_SKIP_ADMIN_COMMUNICATIONS_BLUEPRINT=1 — no registrar /admin/communications ni /api/admin/communications/*.
# NODEONE_SKIP_COMMUNICATION_ENGINE=1 — no ejecutar motor en registro/pagos/eventos (communication_dispatch).
# NODEONE_AUTOMATION_DEFER_TO_COMM_ENGINE=1 — trigger_automation no encola si hay communication_rule para ese evento y org.
# NODEONE_SKIP_ACADEMIC_MODULE=1 — no registrar Educación/LMS (estudiantes, cursos, matrículas, API Moodle).
# NODEONE_ACADEMIC_MODULE_ENABLED=0 — apaga el módulo en todo el despliegue (además del toggle SaaS `academic` por tenant).


def register_academic_module(app):
    if os.environ.get('NODEONE_SKIP_ACADEMIC_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from nodeone.services.academic_module import is_academic_globally_allowed

    if not is_academic_globally_allowed():
        return
    try:
        from nodeone.modules.academic.routes import academic_admin_bp, academic_api_bp

        # No llamar ensure_academic_schema aquí: usa db.session y exige app context;
        # el esquema se crea en before_request de las rutas academic_*.
        if 'academic_admin' not in app.blueprints:
            app.register_blueprint(academic_admin_bp)
        if 'academic_api' not in app.blueprints:
            app.register_blueprint(academic_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar módulo academic: {e}')


def register_media_admin_blueprint(app):
    if os.environ.get('NODEONE_SKIP_MEDIA_ADMIN_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.media_admin.routes import media_admin_bp

        if 'media_admin' not in app.blueprints:
            app.register_blueprint(media_admin_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar media_admin_bp: {e}')


def register_admin_email_api_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_EMAIL_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_email_api.routes import admin_email_bp

        if 'admin_email' not in app.blueprints:
            app.register_blueprint(admin_email_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_email_bp: {e}')


def register_office365_admin_blueprint(app):
    if os.environ.get('NODEONE_SKIP_OFFICE365_ADMIN_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    from nodeone.services.office365_module import is_office365_globally_allowed

    if not is_office365_globally_allowed():
        return
    try:
        from nodeone.modules.office365_admin.routes import office365_admin_bp

        if 'office365_admin' not in app.blueprints:
            app.register_blueprint(office365_admin_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar office365_admin_bp: {e}')


def register_ai_api_blueprint(app):
    if os.environ.get('NODEONE_SKIP_AI_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.ai_api.routes import ai_api_bp

        if 'ai_api' not in app.blueprints:
            app.register_blueprint(ai_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar ai_api_bp: {e}')


def register_admin_tenant_contacts_routes(app):
    """Rutas /admin/contacts (endpoints en app, sin blueprint; compat. saas_features)."""
    if 'admin_tenant_contacts' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_tenant_contacts.routes import register_admin_tenant_contacts_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin tenant contacts: {e}')


def register_admin_benefits_plans_policies_routes(app):
    """Rutas admin benefits, plans, policies (endpoints legacy en app)."""
    if 'admin_benefits' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_benefits_plans_policies.routes import register_admin_benefits_plans_policies_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin benefits/plans/policies: {e}')


def register_admin_certificate_pages_routes(app):
    """Vistas HTML /admin/certificate-events, /admin/certificate-templates, editor."""
    if 'admin_certificate_events' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_certificate_pages.routes import register_admin_certificate_pages_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar vistas admin certificate pages: {e}')


def register_admin_marketing_routes(app):
    """Rutas /admin/marketing/* y API email-config marketing."""
    if 'admin_marketing' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_marketing.routes import register_admin_marketing_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin marketing: {e}')


def register_admin_email_page_routes(app):
    """Vista HTML /admin/email (endpoint legacy en app)."""
    if 'admin_email' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_email_page.routes import register_admin_email_page_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudo registrar vista admin email page: {e}')


def register_admin_saas_pages_routes(app):
    """Vistas /admin/saas-modules y /admin/saas-catalog* (endpoints legacy)."""
    if 'admin_saas_modules_page' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_saas_pages.routes import register_admin_saas_pages_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar vistas admin saas pages: {e}')


def register_admin_crm_routes(app):
    """Vistas admin CRM (/admin/crm*)."""
    if 'admin_crm_dashboard' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_crm.routes import register_admin_crm_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar vistas admin CRM: {e}')


def register_admin_analytics_routes(app):
    """Analytics / KPIs: /admin/analytics* y /api/admin/analytics/*."""
    try:
        from nodeone.modules.analytics.routes import register_admin_analytics_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas analytics: {e}')
        # Fallback: evita 404/500 si alguien navega manualmente a /admin/analytics
        # en despliegues donde el módulo analytics no está presente.
        try:
            from flask import flash, redirect, url_for
            from flask_login import login_required

            if 'admin_analytics' not in getattr(app, 'view_functions', {}):

                @app.route('/admin/analytics')
                @login_required
                def admin_analytics():
                    flash('Analítica no está disponible en este entorno.', 'warning')
                    return redirect(url_for('dashboard'))
        except Exception as fallback_err:
            print(f'Warning: No se pudo registrar fallback de analytics: {fallback_err}')


def register_admin_workshop_pages(app):
    """Vistas /admin/workshop/* (órdenes de taller)."""
    if os.environ.get('NODEONE_SKIP_WORKSHOP_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.workshop.routes import register_admin_workshop_routes as _reg

        _reg(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar vistas admin workshop: {e}')


def register_workshop_blueprints(app):
    """API /api/workshop/* (órdenes, inspección, fotos). Guard SaaS: workshop."""
    if os.environ.get('NODEONE_SKIP_WORKSHOP_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.workshop.routes import register_workshop_saas_default_org_link, workshop_api_bp
        from saas_features import register_simple_saas_guard

        if 'workshop_api' not in app.blueprints:
            register_workshop_saas_default_org_link(workshop_api_bp)
            register_simple_saas_guard(workshop_api_bp, 'workshop')
            app.register_blueprint(workshop_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar workshop_api_bp: {e}')


def register_admin_sales_accounting_routes(app):
    """Vistas admin: impuestos (config) siempre; cotizaciones/facturas según skip."""
    try:
        from nodeone.modules.admin_sales_accounting.routes import register_admin_tax_configuration_routes

        register_admin_tax_configuration_routes(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin configuración impuestos: {e}')
    if os.environ.get('NODEONE_SKIP_ADMIN_SALES_ACCOUNTING_ROUTES', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_sales_accounting.routes import (
            register_admin_accounting_invoice_new_route as _reg_inv_new,
            register_admin_sales_commercial_contacts_routes as _reg_cc,
            register_admin_sales_quotations_invoices_routes as _reg_qi,
        )

        _reg_qi(app)
        _reg_cc(app)
        # Rutas añadidas tras el bloque idempotente de cotizaciones (despliegues parciales sin reinicio limpio).
        _reg_inv_new(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin sales/accounting: {e}')


def register_admin_notifications_identity_routes(app):
    """Vistas/API /admin/notifications* y /admin/identity (endpoints legacy)."""
    if 'admin_notifications' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_notifications_identity.routes import register_admin_notifications_identity_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin notifications/identity: {e}')


def register_admin_communications_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_COMMUNICATIONS_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_communications.routes import admin_communications_bp

        if 'admin_communications' not in app.blueprints:
            app.register_blueprint(admin_communications_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_communications_bp: {e}')


def register_admin_users_roles_routes(app):
    """Rutas /admin/users*, /admin/roles* y APIs de roles/permisos (legacy)."""
    if 'admin_users' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_users_roles.routes import register_admin_users_roles_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin users/roles: {e}')


def register_org_invite_routes(app):
    """GET/POST /api/admin/organization-invites, DELETE revocar, GET /accept-invite/<token>."""
    if 'accept_invite' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.org_invites.routes import register_org_invite_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas org invites: {e}')


def register_admin_messaging_routes(app):
    """Rutas /admin/messaging* y /api/admin/messaging/stats (legacy)."""
    if 'admin_messaging' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_messaging.routes import register_admin_messaging_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin messaging: {e}')


def register_admin_platform_org_routes(app):
    """Rutas /admin/guide-img, /admin/product-guide, /admin/platform-setup, /admin/organizations*."""
    if 'admin_organizations_list' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_platform_org.routes import register_admin_platform_org_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin platform/org: {e}')


def register_admin_dashboard_memberships_routes(app):
    """Rutas /admin, /admin/ y /admin/memberships (legacy)."""
    if 'admin_dashboard' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_dashboard_memberships.routes import register_admin_dashboard_memberships_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas admin dashboard/memberships: {e}')


def register_admin_ai_pages_routes(app):
    """Vistas /admin/ai y /admin/chatbots (legacy)."""
    if 'admin_ai' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.admin_ai_pages.routes import register_admin_ai_pages_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar vistas admin AI: {e}')


def register_public_and_org_switch_routes(app):
    """Rutas /, /promocion, /set-organization y /admin/switch-organization."""
    if 'index' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.public_and_org_switch.routes import register_public_and_org_switch_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas public/org switch: {e}')


def register_public_membership_routes(app):
    """Rutas /dashboard, /membership y /benefits (legacy)."""
    if 'dashboard' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.public_membership.routes import register_public_membership_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas public membership: {e}')


def register_public_auth_legacy_routes(app):
    """Rutas legacy de auth/cuenta publicas (register, verify, oauth, reset, logout)."""
    if 'register' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.public_auth_legacy.routes import register_public_auth_legacy_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas public auth legacy: {e}')


def register_cv_application_routes(app):
    """Formulario público /cv/registro y listado admin /admin/cv-applications."""
    if 'cv_registro' in getattr(app, 'view_functions', {}):
        return
    try:
        from nodeone.modules.cv_applications.routes import register_cv_application_routes as _register

        _register(app)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar rutas CV applications: {e}')


def register_public_api_blueprint(app):
    if os.environ.get('NODEONE_SKIP_PUBLIC_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.public_api.routes import public_api_bp

        if 'public_api' not in app.blueprints:
            app.register_blueprint(public_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar public_api_bp: {e}')


def register_history_admin_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_HISTORY_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.history_api.admin_routes import history_admin_bp

        if 'history_admin' not in app.blueprints:
            app.register_blueprint(history_admin_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar history_admin_bp: {e}')


def register_member_history_blueprint(app):
    if os.environ.get('NODEONE_SKIP_MEMBER_HISTORY_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.history_api.routes import history_member_bp

        if 'history_member' not in app.blueprints:
            app.register_blueprint(history_member_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar history_member_bp: {e}')


def register_user_api_blueprint(app):
    if os.environ.get('NODEONE_SKIP_USER_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.user_api.routes import user_api_bp

        if 'user_api' not in app.blueprints:
            app.register_blueprint(user_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar user_api_bp: {e}')


def register_auth_blueprint(app):
    if os.environ.get('NODEONE_SKIP_AUTH_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from _app.modules.auth.routes import auth_bp

        if 'auth' not in app.blueprints:
            app.register_blueprint(auth_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar el blueprint de auth: {e}')


def register_members_pack_blueprints(app):
    """members + communications + services + integrations (guards antes de register_blueprint)."""
    if os.environ.get('NODEONE_SKIP_MEMBERS_PACK', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from _app.modules.communications.routes import communications_bp
        from _app.modules.members.routes import members_bp
        from _app.modules.services.routes import services_bp
        from nodeone.services.office365_module import is_office365_globally_allowed
        from saas_features import register_services_saas_guards, register_simple_saas_guard

        if 'members' not in app.blueprints:
            register_simple_saas_guard(communications_bp, 'communications')
            register_services_saas_guards(services_bp)
            app.register_blueprint(members_bp)
            app.register_blueprint(communications_bp)
            app.register_blueprint(services_bp)
            if is_office365_globally_allowed():
                from _app.modules.integrations.routes import integrations_bp

                register_simple_saas_guard(integrations_bp, 'communications')
                app.register_blueprint(integrations_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar blueprints members/servicios/comunicaciones: {e}')


def register_policies_blueprint(app):
    if os.environ.get('NODEONE_SKIP_POLICIES_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from _app.modules.policies.routes import policies_bp
        from saas_features import register_policies_public_saas_guard as _reg_pol_guard

        if 'policies' not in app.blueprints:
            _reg_pol_guard(policies_bp)
            app.register_blueprint(policies_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar policies_bp: {e}')


def register_payments_checkout_blueprint(app):
    if os.environ.get('NODEONE_SKIP_PAYMENTS_CHECKOUT_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.payments_checkout.routes import payments_checkout_bp
        from saas_features import register_payments_checkout_saas_guard

        if 'payments_checkout' not in app.blueprints:
            register_payments_checkout_saas_guard(payments_checkout_bp)
            app.register_blueprint(payments_checkout_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar payments_checkout_bp: {e}')


def register_payments_admin_blueprint(app):
    if os.environ.get('NODEONE_SKIP_PAYMENTS_ADMIN_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.payments_admin.routes import payments_admin_bp
        from saas_features import register_simple_saas_guard as _reg_pay_admin_guard

        if 'payments_admin' not in app.blueprints:
            _reg_pay_admin_guard(payments_admin_bp, 'payments')
            app.register_blueprint(payments_admin_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar payments_admin_bp: {e}')


def register_admin_export_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_EXPORT_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_export.routes import admin_export_bp

        if 'admin_export' not in app.blueprints:
            app.register_blueprint(admin_export_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_export_bp: {e}')


def register_admin_backup_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_BACKUP_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_backup.routes import admin_backup_bp

        if 'admin_backup' not in app.blueprints:
            app.register_blueprint(admin_backup_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_backup_bp: {e}')


def register_admin_discount_codes_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_DISCOUNT_CODES_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_discount_codes.routes import admin_discount_codes_bp

        if 'admin_discount_codes' not in app.blueprints:
            app.register_blueprint(admin_discount_codes_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_discount_codes_bp: {e}')


def register_admin_membership_discounts_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_MEMBERSHIP_DISCOUNTS_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_membership_discounts.routes import admin_membership_discounts_bp

        if 'admin_membership_discounts' not in app.blueprints:
            app.register_blueprint(admin_membership_discounts_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_membership_discounts_bp: {e}')


def register_admin_services_catalog_blueprint(app):
    if os.environ.get('NODEONE_SKIP_ADMIN_SERVICES_CATALOG_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.admin_services_catalog.routes import admin_services_catalog_bp

        if 'admin_services_catalog' not in app.blueprints:
            app.register_blueprint(admin_services_catalog_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar admin_services_catalog_bp: {e}')


def register_member_community_blueprint(app):
    if os.environ.get('NODEONE_SKIP_MEMBER_COMMUNITY_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.member_community.routes import member_community_bp

        if 'member_community' not in app.blueprints:
            app.register_blueprint(member_community_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar member_community_bp: {e}')


def register_member_pages_blueprint(app):
    if os.environ.get('NODEONE_SKIP_MEMBER_PAGES_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.member_pages.routes import member_pages_bp

        if 'member_pages' not in app.blueprints:
            app.register_blueprint(member_pages_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar member_pages_bp: {e}')


def register_payments_blueprint(app):
    if os.environ.get('NODEONE_SKIP_PAYMENTS_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from _app.modules.payments.routes import payments_bp
        from saas_features import register_simple_saas_guard as _reg_pay_guard

        if 'payments' not in app.blueprints:
            _reg_pay_guard(payments_bp, 'payments')
            app.register_blueprint(payments_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar payments_bp: {e}')


def register_appointments_blueprints(app):
    """
    Registra citas (appointments) + API slots asesor.
    Idempotente por blueprint (p. ej. tests o imports que llamen register_modules de nuevo).
    """
    if os.environ.get('NODEONE_SKIP_APPOINTMENTS_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.appointments.advisor_slots_api import advisor_slots_api_bp
        from nodeone.modules.appointments.routes import (
            admin_appointments_bp,
            appointments_api_bp,
            appointments_bp,
            appointments_http_legacy_bp,
        )
        from saas_features import register_appointments_saas_guards

        # Flask 3+: before_request en el blueprint antes de register_blueprint.
        if 'appointments' not in app.blueprints:
            register_appointments_saas_guards(
                appointments_bp,
                admin_appointments_bp,
                appointments_api_bp,
                advisor_slots_api_bp,
                appointments_http_legacy_bp,
            )
            app.register_blueprint(appointments_bp)
            app.register_blueprint(admin_appointments_bp)
            app.register_blueprint(appointments_api_bp)
            app.register_blueprint(advisor_slots_api_bp)
            app.register_blueprint(appointments_http_legacy_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar los blueprints de citas: {e}')
        return


def register_events_blueprints(app):
    """Blueprints de eventos + guards SaaS (Flask 3: guards antes de register_blueprint)."""
    if os.environ.get('NODEONE_SKIP_EVENTS_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.events.routes import admin_events_bp, events_api_bp, events_bp
        from saas_features import register_events_saas_guards

        if 'events' not in app.blueprints:
            register_events_saas_guards(events_bp, admin_events_bp, events_api_bp)
            app.register_blueprint(events_bp)
            app.register_blueprint(admin_events_bp)
            app.register_blueprint(events_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar los blueprints de eventos: {e}')


def register_certificates_blueprints(app):
    """Certificados (API, público, plantillas, builder) + guards SaaS."""
    if os.environ.get('NODEONE_SKIP_CERTIFICATES_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from certificate_routes import (
            certificates_api_bp,
            certificates_page_bp,
            certificates_public_bp,
        )
        from certificate_template_routes import certificate_templates_bp
        from certificates_builder.routes import certificates_builder_bp, certificates_builder_page_bp
        from saas_features import register_certificates_saas_guards

        if 'certificates_api' not in app.blueprints:
            register_certificates_saas_guards(
                certificates_api_bp,
                certificates_page_bp,
                certificate_templates_bp,
                certificates_builder_bp,
                certificates_builder_page_bp,
            )
            app.register_blueprint(certificates_api_bp)
            app.register_blueprint(certificates_public_bp)
            app.register_blueprint(certificates_page_bp)
            app.register_blueprint(certificate_templates_bp)
            app.register_blueprint(certificates_builder_bp)
            app.register_blueprint(certificates_builder_page_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar los blueprints de certificados: {e}')


def register_marketing_blueprint(app):
    """Marketing (campañas) + guard SaaS."""
    if os.environ.get('NODEONE_SKIP_MARKETING_MODULE', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from _app.modules.marketing.routes import marketing_bp
        from saas_features import register_marketing_saas_guard

        if 'marketing' not in app.blueprints:
            register_marketing_saas_guard(marketing_bp)
            app.register_blueprint(marketing_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar los blueprints de marketing: {e}')


def register_crm_api_blueprint(app):
    """API CRM (/crm/*): leads, etapas, actividades, reportes."""
    if os.environ.get('NODEONE_SKIP_CRM_API_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from nodeone.modules.crm_api.routes import crm_api_bp

        if 'crm_api' not in app.blueprints:
            app.register_blueprint(crm_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar crm_api_bp: {e}')


def _register_tax_api_blueprints(app):
    """Registra solo /taxes y /api/taxes (sin módulo ventas en cotizaciones)."""
    try:
        from nodeone.modules.accounting.routes import taxes_api_bp, taxes_bp

        if 'accounting_taxes' not in app.blueprints:
            app.register_blueprint(taxes_bp)
        if 'accounting_taxes_api' not in app.blueprints:
            app.register_blueprint(taxes_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar blueprints de impuestos: {e}')


def register_sales_accounting_blueprints(app):
    """Cotizaciones JSON (/api/sales/quotations), facturas (/invoices) e impuestos (/taxes); guard SaaS: sales."""
    if os.environ.get('NODEONE_SKIP_SALES_ACCOUNTING_BLUEPRINT', '').strip().lower() in ('1', 'true', 'yes'):
        _register_tax_api_blueprints(app)
        return
    try:
        from nodeone.modules.accounting.routes import accounting_bp, taxes_api_bp, taxes_bp
        from nodeone.modules.sales.routes import sales_bp
        from saas_features import register_simple_saas_guard

        # Flask 3+: before_request en el blueprint antes de register_blueprint.
        if 'sales' not in app.blueprints:
            register_simple_saas_guard(sales_bp, 'sales')
            app.register_blueprint(sales_bp)
        if 'accounting' not in app.blueprints:
            register_simple_saas_guard(accounting_bp, 'sales')
            app.register_blueprint(accounting_bp)
        if 'accounting_taxes' not in app.blueprints:
            app.register_blueprint(taxes_bp)
        if 'accounting_taxes_api' not in app.blueprints:
            app.register_blueprint(taxes_api_bp)
    except ImportError as e:
        print(f'Warning: No se pudieron registrar sales/accounting blueprints: {e}')


def register_saas_admin_blueprint(app):
    """API JSON módulos SaaS por organización (/api/admin/saas)."""
    if os.environ.get('NODEONE_SKIP_SAAS_ADMIN_API', '').strip().lower() in ('1', 'true', 'yes'):
        return
    try:
        from saas_admin_api import saas_admin_bp

        if 'saas_admin' not in app.blueprints:
            app.register_blueprint(saas_admin_bp)
    except ImportError as e:
        print(f'Warning: No se pudo registrar saas_admin_bp: {e}')


def register_modules(app):
    """Orquestación completa de blueprints _app + nodeone (idempotente)."""
    register_admin_tenant_contacts_routes(app)
    register_admin_benefits_plans_policies_routes(app)
    register_admin_certificate_pages_routes(app)
    register_admin_marketing_routes(app)
    register_admin_email_page_routes(app)
    register_admin_saas_pages_routes(app)
    register_saas_admin_blueprint(app)
    register_admin_crm_routes(app)
    register_admin_analytics_routes(app)
    register_admin_sales_accounting_routes(app)
    register_admin_workshop_pages(app)
    register_admin_notifications_identity_routes(app)
    register_admin_communications_blueprint(app)
    register_admin_users_roles_routes(app)
    register_org_invite_routes(app)
    register_admin_messaging_routes(app)
    register_admin_platform_org_routes(app)
    register_admin_dashboard_memberships_routes(app)
    register_admin_ai_pages_routes(app)
    register_public_and_org_switch_routes(app)
    register_public_membership_routes(app)
    register_public_auth_legacy_routes(app)
    register_cv_application_routes(app)
    register_public_api_blueprint(app)
    register_ai_api_blueprint(app)
    register_admin_email_api_blueprint(app)
    register_media_admin_blueprint(app)
    register_office365_admin_blueprint(app)
    register_user_api_blueprint(app)
    register_member_history_blueprint(app)
    register_history_admin_blueprint(app)
    register_auth_blueprint(app)
    register_members_pack_blueprints(app)
    register_member_community_blueprint(app)
    register_member_pages_blueprint(app)
    register_policies_blueprint(app)
    register_payments_blueprint(app)
    register_payments_checkout_blueprint(app)
    register_payments_admin_blueprint(app)
    register_admin_export_blueprint(app)
    register_admin_backup_blueprint(app)
    register_admin_discount_codes_blueprint(app)
    register_admin_membership_discounts_blueprint(app)
    register_admin_services_catalog_blueprint(app)
    register_appointments_blueprints(app)
    register_events_blueprints(app)
    register_certificates_blueprints(app)
    register_marketing_blueprint(app)
    register_crm_api_blueprint(app)
    register_sales_accounting_blueprints(app)
    register_workshop_blueprints(app)
    register_academic_module(app)


def init_extensions(app):
    """FASE 1: db/login/mail viven en el monolito al importar app."""
    pass
