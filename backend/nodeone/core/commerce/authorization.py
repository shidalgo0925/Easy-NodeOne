"""Autorización supervisor — dominio comercial Etapa 7."""

from __future__ import annotations

from typing import Any

from nodeone.core.commerce.events import COMMERCE_AUTHORIZATION_APPLIED
from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.services.audit import AuditService


class CommerceAuthorizationService:
    @staticmethod
    def user_is_supervisor(user, organization_id: int) -> bool:
        if user is None or not getattr(user, 'id', None):
            return False
        if getattr(user, 'is_admin', False):
            return True
        from nodeone.services.admin_tenant_access import user_has_any_rbac_admin_permission
        from nodeone.services.user_organization import user_has_active_membership

        if not user_has_any_rbac_admin_permission(user):
            return False
        return user_has_active_membership(user, int(organization_id))

    @staticmethod
    def assert_supervisor(
        organization_id: int,
        approval: dict[str, Any],
        *,
        action: str,
        order_id: int | None = None,
        order_ref: str | None = None,
        payment_id: int | None = None,
        shift_id: int | None = None,
        source_app_id: str = 'eposone',
    ) -> int:
        try:
            from nodeone.modules.eposone.settings_service import EposoneSettingsService

            if not EposoneSettingsService.runtime_for(int(organization_id)).supervisor_approval_required:
                raw_optional = approval.get('supervisor_user_id')
                if raw_optional:
                    from models.users import User

                    user = User.query.get(int(raw_optional))
                    if user is not None:
                        return int(user.id)
                return 0
        except Exception:
            pass

        raw_id = approval.get('supervisor_user_id')
        if not raw_id:
            raise OrderValidationError('supervisor_required')

        from models.users import User

        user = User.query.get(int(raw_id))
        if user is None:
            raise OrderValidationError('supervisor_not_found')
        if not CommerceAuthorizationService.user_is_supervisor(user, int(organization_id)):
            raise OrderValidationError('supervisor_not_authorized')

        reason = (approval.get('reason') or approval.get('supervisor_reason') or '').strip() or None
        CommerceAuthorizationService.publish_applied(
            int(organization_id),
            supervisor_user_id=int(user.id),
            action=str(action),
            reason=reason,
            order_id=order_id,
            order_ref=order_ref,
            payment_id=payment_id,
            shift_id=shift_id,
            source_app_id=source_app_id,
        )
        return int(user.id)

    @staticmethod
    def publish_applied(
        organization_id: int,
        *,
        supervisor_user_id: int,
        action: str,
        reason: str | None = None,
        order_id: int | None = None,
        order_ref: str | None = None,
        payment_id: int | None = None,
        shift_id: int | None = None,
        source_app_id: str = 'eposone',
    ):
        payload: dict[str, Any] = {
            'user_id': int(supervisor_user_id),
            'action': str(action),
        }
        if reason:
            payload['reason'] = reason
        if order_id is not None:
            payload['order_id'] = int(order_id)
        if order_ref:
            payload['order_ref'] = order_ref
        if payment_id is not None:
            payload['payment_id'] = int(payment_id)
        if shift_id is not None:
            payload['shift_id'] = int(shift_id)
        return AuditService.publish_domain_event(
            organization_id,
            COMMERCE_AUTHORIZATION_APPLIED,
            payload,
            source_app_id=source_app_id,
        )
