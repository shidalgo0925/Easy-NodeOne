"""
Sincronía entre NotificationSettings (legacy) y CommunicationRule:

- Legacy → reglas: mismo código que communication_event.code.
- Reglas → legacy: si hay al menos una regla para el evento, legacy.enabled refleja
  “hay alguna regla activa”; si no hay reglas, no se toca legacy.
"""

from __future__ import annotations

from datetime import datetime


def sync_event_rules_to_notification_settings(event_id: int) -> bool:
    """
    Actualiza NotificationSettings.enabled según si queda alguna regla activa
    para ese communication_event (mismo code que notification_type).
    No modifica legacy si no existe fila NotificationSettings o no hay reglas.
    """
    import app as M

    from app import NotificationSettings
    from models.communication_rules import CommunicationEvent, CommunicationRule

    ev = CommunicationEvent.query.get(event_id)
    if not ev:
        return False
    ns = NotificationSettings.query.filter_by(notification_type=ev.code).first()
    if not ns:
        return False
    n_rules = CommunicationRule.query.filter_by(event_id=event_id).count()
    if n_rules == 0:
        return False
    any_active = (
        CommunicationRule.query.filter_by(event_id=event_id, enabled=True).first() is not None
    )
    if ns.enabled == any_active:
        return False
    ns.enabled = any_active
    ns.updated_at = datetime.utcnow()
    M.db.session.commit()
    return True


def sync_notification_type_to_communication_rules(notification_type: str, enabled: bool) -> int:
    """
    Iguala CommunicationRule.enabled al toggle legacy para ese código de evento.
    Retorna cuántas reglas se modificaron.
    """
    if not notification_type or not isinstance(notification_type, str):
        return 0
    import app as M

    from models.communication_rules import CommunicationEvent, CommunicationRule

    ev = CommunicationEvent.query.filter_by(code=notification_type.strip()).first()
    if not ev:
        return 0
    want = bool(enabled)
    changed = 0
    for rule in CommunicationRule.query.filter_by(event_id=ev.id).all():
        if rule.enabled != want:
            rule.enabled = want
            changed += 1
    if changed:
        M.db.session.commit()
    return changed


def sync_all_notification_settings_to_rules() -> dict:
    """Alineación masiva (p. ej. migración). Retorna {code: rules_updated_count}."""
    import app as M

    from app import NotificationSettings

    out: dict = {}
    for row in NotificationSettings.query.all():
        n = sync_notification_type_to_communication_rules(row.notification_type, row.enabled)
        if n:
            out[row.notification_type] = n
    return out
