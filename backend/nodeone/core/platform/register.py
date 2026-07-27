"""
Registro de blueprints — Core vs Apps (Etapa 2).

Separa el wiring de ``register_modules`` sin cambiar el conjunto de blueprints.
"""


def register_platform_core(app) -> None:
    """Blueprints y rutas del Core (auth, tenant, RBAC, licenciamiento, servicios compartidos)."""
    from nodeone.core import features as f

    f.register_admin_tenant_contacts_routes(app)
    f.register_admin_saas_pages_routes(app)
    f.register_saas_admin_blueprint(app)
    f.register_admin_users_roles_routes(app)
    f.register_org_invite_routes(app)
    f.register_admin_platform_org_routes(app)
    f.register_public_and_org_switch_routes(app)
    f.register_public_auth_legacy_routes(app)
    f.register_public_api_blueprint(app)
    f.register_ai_api_blueprint(app)
    f.register_admin_ai_pages_routes(app)
    f.register_admin_email_api_blueprint(app)
    f.register_admin_email_page_routes(app)
    f.register_media_admin_blueprint(app)
    f.register_admin_notifications_identity_routes(app)
    f.register_user_api_blueprint(app)
    f.register_history_admin_blueprint(app)
    f.register_auth_blueprint(app)
    f.register_payments_blueprint(app)
    f.register_payments_checkout_blueprint(app)
    f.register_payments_admin_blueprint(app)
    f.register_admin_export_blueprint(app)
    f.register_admin_backup_blueprint(app)
    f.register_contacts_blueprints(app)
    f.register_security_matrix_blueprints(app)
    from nodeone.modules.platform_launcher.routes import register_platform_launcher

    register_platform_launcher(app)
    from nodeone.modules.ets_portal.register import register_ets_portal

    register_ets_portal(app)
    from nodeone.core.sync.routes import register_platform_sync_blueprint

    register_platform_sync_blueprint(app)
    from nodeone.core.platform.apps_routes import register_platform_apps_api

    register_platform_apps_api(app)
    from nodeone.core.platform.master_routes import register_platform_master_api

    register_platform_master_api(app)
    from nodeone.core.commerce.register import register_commerce_bus_handlers

    register_commerce_bus_handlers()
    from nodeone.core.platform.manifest_registry import warn_registry_misalignment

    warn_registry_misalignment()


def register_platform_apps(app) -> None:
    """Blueprints de aplicaciones de negocio (dominios activables por tenant)."""
    from nodeone.core import features as f

    f.register_admin_benefits_plans_policies_routes(app)
    f.register_admin_certificate_pages_routes(app)
    f.register_admin_marketing_routes(app)
    f.register_admin_crm_routes(app)
    f.register_admin_analytics_routes(app)
    f.register_admin_service_metrics_routes(app)
    f.register_admin_sales_accounting_routes(app)
    f.register_admin_workshop_pages(app)
    f.register_admin_communications_blueprint(app)
    f.register_admin_messaging_routes(app)
    f.register_admin_dashboard_memberships_routes(app)
    f.register_public_membership_routes(app)
    f.register_cv_application_routes(app)
    f.register_public_program_routes(app)
    f.register_ecalendar_blueprint(app)
    f.register_ecalendar_admin_routes(app)
    f.register_office365_admin_blueprint(app)
    f.register_member_history_blueprint(app)
    f.register_members_pack_blueprints(app)
    f.register_member_community_blueprint(app)
    f.register_member_pages_blueprint(app)
    f.register_policies_blueprint(app)
    f.register_academic_enrollment_admin_blueprint(app)
    f.register_admin_discount_codes_blueprint(app)
    f.register_admin_membership_discounts_blueprint(app)
    f.register_admin_services_catalog_blueprint(app)
    f.register_admin_course_cohort_routes(app)
    f.register_appointments_blueprints(app)
    f.register_events_blueprints(app)
    f.register_certificates_blueprints(app)
    f.register_marketing_blueprint(app)
    f.register_crm_api_blueprint(app)
    f.register_sales_accounting_blueprints(app)
    f.register_accounting_core_blueprint(app)
    f.register_workshop_blueprints(app)
    f.register_academic_module(app)
    f.register_contador_blueprints(app)
    f.register_efactura_blueprints(app)
    f.register_eposone_blueprints(app)
    f.register_epayroll_blueprints(app)
    f.register_qr_generator_routes(app)
    f.register_qr_tools_routes(app)
