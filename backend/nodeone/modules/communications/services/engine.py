"""
Motor central de comunicaciones (Fase 1).

Evalúa reglas por código de evento, preferencias de usuario y opcionalmente
NotificationSettings legado. Las acciones concretas (encolar email, crear in-app)
se delegan en hooks inyectables para tests y migración gradual.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import or_

from nodeone.core.db import db

# Import lazy de modelos para evitar ciclos al cargar app
_communication_models = None


def _models():
    global _communication_models
    if _communication_models is None:
        from models.communication_rules import (
            CommunicationEvent,
            CommunicationLog,
            CommunicationRule,
            UserCommunicationPreference,
        )

        _communication_models = (
            CommunicationEvent,
            CommunicationLog,
            CommunicationRule,
            UserCommunicationPreference,
        )
    return _communication_models


@dataclass
class CommunicationHooks:
    """Callbacks opcionales por canal. Si son None, solo se registra log 'executed'."""

    enqueue_email: Optional[Callable[..., None]] = None
    create_in_app: Optional[Callable[..., None]] = None
    enqueue_sms: Optional[Callable[..., None]] = None


@dataclass
class TriggerAction:
    rule_id: int
    channel: str
    status: str
    detail: str = ''


@dataclass
class TriggerResult:
    event_code: str
    user_id: Optional[int]
    actions: List[TriggerAction] = field(default_factory=list)
    log_ids: List[int] = field(default_factory=list)


def _user_allows_channel(
    user_id: int,
    event_id: int,
    channel: str,
    UserCommunicationPreference,
) -> bool:
    row = (
        UserCommunicationPreference.query.filter_by(
            user_id=user_id,
            event_id=event_id,
            channel=channel,
        ).first()
    )
    if row is None:
        return True
    return bool(row.enabled)


def _legacy_notification_enabled(notification_type: str) -> bool:
    """Si existe NotificationSettings y el tipo está deshabilitado, retorna False."""
    try:
        import app as M

        if not hasattr(M, 'NotificationSettings'):
            return True
        return M.NotificationSettings.is_enabled(notification_type)
    except Exception:
        return True


def _log(
    CommunicationLog,
    *,
    user_id: Optional[int],
    event_id: Optional[int],
    rule_id: Optional[int],
    channel: Optional[str],
    status: str,
    message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> int:
    ctx = json.dumps(context, ensure_ascii=False, default=str) if context else None
    row = CommunicationLog(
        user_id=user_id,
        event_id=event_id,
        rule_id=rule_id,
        channel=channel,
        status=status,
        message=message,
        context_json=ctx,
    )
    db.session.add(row)
    db.session.flush()
    return int(row.id)


class CommunicationEngine:
    @staticmethod
    def trigger(
        event_code: str,
        user_id: int,
        *,
        organization_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        hooks: Optional[CommunicationHooks] = None,
        use_legacy_notification_settings: bool = False,
        legacy_notification_type: Optional[str] = None,
        commit: bool = True,
    ) -> TriggerResult:
        """
        Dispara evaluación de reglas para un evento y usuario.

        use_legacy_notification_settings: si True, consulta NotificationSettings
        con legacy_notification_type o event_code antes de evaluar reglas.
        """
        (
            CommunicationEvent,
            CommunicationLog,
            CommunicationRule,
            UserCommunicationPreference,
        ) = _models()

        ctx = dict(context or {})
        result = TriggerResult(event_code=event_code, user_id=user_id)

        if use_legacy_notification_settings:
            ltype = legacy_notification_type or event_code
            if not _legacy_notification_enabled(ltype):
                ev = CommunicationEvent.query.filter_by(code=event_code).first()
                eid = ev.id if ev else None
                lid = _log(
                    CommunicationLog,
                    user_id=user_id,
                    event_id=eid,
                    rule_id=None,
                    channel=None,
                    status='skipped_legacy_settings',
                    message=f'NotificationSettings disabled: {ltype}',
                    context=ctx,
                )
                result.log_ids.append(lid)
                if commit:
                    db.session.commit()
                return result

        event = CommunicationEvent.query.filter_by(code=event_code).first()
        if event is None:
            lid = _log(
                CommunicationLog,
                user_id=user_id,
                event_id=None,
                rule_id=None,
                channel=None,
                status='skipped_unknown_event',
                message=f'No communication_event for code={event_code}',
                context=ctx,
            )
            result.log_ids.append(lid)
            if commit:
                db.session.commit()
            return result

        q = CommunicationRule.query.filter_by(event_id=event.id, enabled=True)
        if organization_id is not None:
            oid = int(organization_id)
            q = q.filter(
                or_(
                    CommunicationRule.organization_id.is_(None),
                    CommunicationRule.organization_id == oid,
                )
            )
        rules = q.order_by(CommunicationRule.priority.asc(), CommunicationRule.id.asc()).all()

        if not rules:
            lid = _log(
                CommunicationLog,
                user_id=user_id,
                event_id=event.id,
                rule_id=None,
                channel=None,
                status='skipped_no_rules',
                message='No active rules for this event/org scope',
                context=ctx,
            )
            result.log_ids.append(lid)
            if commit:
                db.session.commit()
            return result

        hooks = hooks or CommunicationHooks()

        for rule in rules:
            ch = (rule.channel or '').strip().lower()
            if rule.respect_user_prefs and not _user_allows_channel(
                user_id, event.id, ch, UserCommunicationPreference
            ):
                lid = _log(
                    CommunicationLog,
                    user_id=user_id,
                    event_id=event.id,
                    rule_id=rule.id,
                    channel=ch,
                    status='skipped_user_preference',
                    message='User disabled this channel for event',
                    context=ctx,
                )
                result.log_ids.append(lid)
                result.actions.append(
                    TriggerAction(rule_id=rule.id, channel=ch, status='skipped_user_preference')
                )
                continue

            if rule.delay_minutes and int(rule.delay_minutes) > 0:
                lid = _log(
                    CommunicationLog,
                    user_id=user_id,
                    event_id=event.id,
                    rule_id=rule.id,
                    channel=ch,
                    status='pending_delay',
                    message=f'delay_minutes={rule.delay_minutes}',
                    context=ctx,
                )
                result.log_ids.append(lid)
                result.actions.append(
                    TriggerAction(
                        rule_id=rule.id,
                        channel=ch,
                        status='pending_delay',
                        detail=str(rule.delay_minutes),
                    )
                )
                if hooks.enqueue_email and ch == 'email':
                    try:
                        hooks.enqueue_email(
                            rule=rule,
                            user_id=user_id,
                            organization_id=organization_id,
                            context=ctx,
                            delay_minutes=int(rule.delay_minutes),
                        )
                    except Exception as ex:  # noqa: BLE001
                        _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='failed',
                            message=str(ex),
                            context=ctx,
                        )
                continue

            if ch == 'email':
                if hooks.enqueue_email:
                    try:
                        hooks.enqueue_email(
                            rule=rule,
                            user_id=user_id,
                            organization_id=organization_id,
                            context=ctx,
                            delay_minutes=0,
                        )
                        lid = _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='executed',
                            message='email hook ok',
                            context=ctx,
                        )
                        result.log_ids.append(lid)
                        result.actions.append(
                            TriggerAction(rule_id=rule.id, channel=ch, status='executed')
                        )
                    except Exception as ex:  # noqa: BLE001
                        lid = _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='failed',
                            message=str(ex),
                            context=ctx,
                        )
                        result.log_ids.append(lid)
                        result.actions.append(
                            TriggerAction(rule_id=rule.id, channel=ch, status='failed', detail=str(ex))
                        )
                else:
                    lid = _log(
                        CommunicationLog,
                        user_id=user_id,
                        event_id=event.id,
                        rule_id=rule.id,
                        channel=ch,
                        status='executed',
                        message='no email hook o regla sin plantilla marketing',
                        context=ctx,
                    )
                    result.log_ids.append(lid)
                    result.actions.append(
                        TriggerAction(rule_id=rule.id, channel=ch, status='executed_no_hook')
                    )

            elif ch == 'in_app':
                if hooks.create_in_app:
                    try:
                        hooks.create_in_app(
                            rule=rule,
                            user_id=user_id,
                            organization_id=organization_id,
                            context=ctx,
                        )
                        lid = _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='executed',
                            message='in_app hook ok',
                            context=ctx,
                        )
                        result.log_ids.append(lid)
                        result.actions.append(
                            TriggerAction(rule_id=rule.id, channel=ch, status='executed')
                        )
                    except Exception as ex:  # noqa: BLE001
                        lid = _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='failed',
                            message=str(ex),
                            context=ctx,
                        )
                        result.log_ids.append(lid)
                else:
                    lid = _log(
                        CommunicationLog,
                        user_id=user_id,
                        event_id=event.id,
                        rule_id=rule.id,
                        channel=ch,
                        status='executed',
                        message='no in_app hook (phase 1 noop)',
                        context=ctx,
                    )
                    result.log_ids.append(lid)
                    result.actions.append(
                        TriggerAction(rule_id=rule.id, channel=ch, status='executed_no_hook')
                    )

            elif ch == 'sms':
                if hooks.enqueue_sms:
                    try:
                        hooks.enqueue_sms(
                            rule=rule,
                            user_id=user_id,
                            organization_id=organization_id,
                            context=ctx,
                        )
                        lid = _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='executed',
                            message='sms hook ok',
                            context=ctx,
                        )
                        result.log_ids.append(lid)
                    except Exception as ex:  # noqa: BLE001
                        _log(
                            CommunicationLog,
                            user_id=user_id,
                            event_id=event.id,
                            rule_id=rule.id,
                            channel=ch,
                            status='failed',
                            message=str(ex),
                            context=ctx,
                        )
                else:
                    lid = _log(
                        CommunicationLog,
                        user_id=user_id,
                        event_id=event.id,
                        rule_id=rule.id,
                        channel=ch,
                        status='executed',
                        message='no sms hook (phase 1 noop)',
                        context=ctx,
                    )
                    result.log_ids.append(lid)
            else:
                lid = _log(
                    CommunicationLog,
                    user_id=user_id,
                    event_id=event.id,
                    rule_id=rule.id,
                    channel=ch,
                    status='skipped_unknown_channel',
                    message=ch,
                    context=ctx,
                )
                result.log_ids.append(lid)

        if commit:
            db.session.commit()
        return result
