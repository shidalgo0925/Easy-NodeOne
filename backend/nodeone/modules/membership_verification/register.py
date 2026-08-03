"""Registro del módulo membership_verification."""


def register_membership_verification_module(app) -> None:
    from nodeone.modules.membership_verification.routes import register_membership_verification

    register_membership_verification(app)
