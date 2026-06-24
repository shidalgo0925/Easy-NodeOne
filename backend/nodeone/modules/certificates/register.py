"""Registro de blueprints del módulo certificados."""


def register_certificates_blueprints(app):
    from saas_features import register_certificates_saas_guards

    from nodeone.modules.certificates.api_routes import (
        certificates_api_bp,
        certificates_page_bp,
        certificates_public_bp,
    )
    from nodeone.modules.certificates.builder.routes import (
        certificates_builder_bp,
        certificates_builder_page_bp,
    )
    from nodeone.modules.certificates.template_routes import certificate_templates_bp

    if 'certificates_api' in app.blueprints:
        return
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
