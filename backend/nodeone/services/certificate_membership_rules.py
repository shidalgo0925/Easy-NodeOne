"""Reglas de elegibilidad y siembra de certificados por plan de membresía."""

from __future__ import annotations

from datetime import datetime, timedelta

_SKIP_PLAN_SLUGS = frozenset({'admin'})


def resolve_membership_org_id(user, org_id: int | None = None) -> int:
    if org_id is not None:
        return int(org_id)
    try:
        from app import tenant_data_organization_id

        return int(tenant_data_organization_id())
    except Exception:
        return int(getattr(user, 'organization_id', None) or 1)


def get_user_currently_active_membership_record(user_id: int):
    """Suscripción vigente o fila Membership activa y no vencida."""
    from models.benefits import Membership
    from models.payments import Subscription

    uid = int(user_id)
    sub = (
        Subscription.query.filter_by(user_id=uid, status='active')
        .filter(Subscription.end_date > datetime.utcnow())
        .order_by(Subscription.id.desc())
        .first()
    )
    if sub is not None:
        return sub
    mem = (
        Membership.query.filter_by(user_id=uid, is_active=True)
        .order_by(Membership.id.desc())
        .first()
    )
    if mem is not None and mem.is_currently_active():
        return mem
    return None


def user_active_membership_plan_id(user, org_id: int | None = None) -> int | None:
    """ID del plan de membresía vigente del usuario en la organización dada."""
    from app import MembershipPlan

    active = get_user_currently_active_membership_record(int(user.id))
    if active is None:
        return None

    mt = (getattr(active, 'membership_type', None) or '').strip()
    if not mt or mt == 'admin':
        return None

    oid = resolve_membership_org_id(user, org_id)
    plan = (
        MembershipPlan.query.filter_by(organization_id=oid, slug=mt, is_active=True).first()
        or MembershipPlan.query.filter_by(organization_id=oid, name=mt, is_active=True).first()
    )
    return int(plan.id) if plan else None


def _normalize_email(value: str | None) -> str:
    return (value or '').strip().lower()


def user_participated_in_event(user, event_id: int) -> bool:
    """
    Participación real en un evento (módulo Eventos): check-in, asistió o revisor.
    No basta con inscripción confirmada sin asistencia.
    """
    from sqlalchemy import and_, func, or_

    from app import EventParticipant
    from nodeone.modules.events.services.certificates import participant_eligible_for_certificate

    try:
        eid = int(event_id)
        uid = int(user.id)
    except (TypeError, ValueError):
        return False

    u_email = _normalize_email(getattr(user, 'email', None))
    clauses = [EventParticipant.user_id == uid]
    if u_email:
        clauses.append(
            and_(
                EventParticipant.user_id.is_(None),
                func.lower(func.trim(EventParticipant.email)) == u_email,
            )
        )

    for participant in EventParticipant.query.filter(
        EventParticipant.event_id == eid,
        or_(*clauses),
    ).all():
        if participant_eligible_for_certificate(participant):
            return True
    return False


def user_qualified_for_certificate_event(user, cert_event, org_id: int | None = None) -> bool:
    prefix = (cert_event.code_prefix or '').strip().upper()
    if prefix == 'REG':
        return True

    if cert_event.membership_required_id is not None:
        user_plan_id = user_active_membership_plan_id(user, org_id)
        if user_plan_id is None:
            return False
        if int(user_plan_id) != int(cert_event.membership_required_id):
            return False

    if cert_event.event_required_id is not None:
        if not user_participated_in_event(user, int(cert_event.event_required_id)):
            return False

    if cert_event.membership_required_id is None and cert_event.event_required_id is None:
        if prefix.startswith('MEM') or prefix.startswith('PLAN'):
            return user_active_membership_plan_id(user, org_id) is not None
        # REL u otros formatos huérfanos (p. ej. seminario sin event_required_id): no autoservicio.
        return False

    return True


def requirement_text_for_certificate_event(cert_event) -> str:
    if (cert_event.code_prefix or '').strip().upper() == 'REG':
        return 'Usuario registrado'
    if cert_event.membership_required_id is not None and cert_event.membership_plan:
        return f'Membresía: plan {cert_event.membership_plan.name}'
    if cert_event.event_required_id is not None and cert_event.event_required:
        return f'Participación en evento: {cert_event.event_required.title}'
    return 'Membresía activa'


def membership_certificate_events_visible_to_user(user, cert_events, org_id: int | None = None):
    """
    Formatos de membresía/registro visibles en Mis Certificados.
    Oculta REG si el usuario ya califica para el certificado del plan Básico (evita duplicado).
    """
    oid = resolve_membership_org_id(user, org_id)
    from app import MembershipPlan

    basic_plan = MembershipPlan.query.filter_by(organization_id=oid, slug='basic', is_active=True).first()
    basic_cert_id = None
    if basic_plan is not None:
        for ev in cert_events:
            if getattr(ev, 'membership_required_id', None) == int(basic_plan.id):
                basic_cert_id = int(ev.id)
                break
    user_has_basic = (
        basic_plan is not None
        and user_active_membership_plan_id(user, oid) == int(basic_plan.id)
    )

    visible = []
    for ev in cert_events:
        prefix = (getattr(ev, 'code_prefix', None) or '').strip().upper()
        if prefix == 'REG' and user_has_basic and basic_cert_id is not None:
            continue
        visible.append(ev)
    return visible


def _plan_code_prefix(slug: str) -> str:
    s = (slug or 'plan').strip().upper().replace(' ', '-')[:16]
    return f'PLAN-{s}'[:20]


def _is_orphan_certificate_event(cert_event) -> bool:
    """Sin plan de membresía ni evento EN1 vinculado."""
    return (
        cert_event.membership_required_id is None
        and cert_event.event_required_id is None
    )


def _purge_orphan_certificate_event_formats(db, oid: int) -> dict:
    """
    Elimina formatos huérfanos sin emisiones y desactiva el resto (REL/MEM sueltos).
    REG legacy se mantiene solo inactivo si ya tiene certificados emitidos.
    """
    from app import Certificate, CertificateEvent, MembershipPlan

    oid = int(oid)
    stats = {'deactivated': 0, 'deleted': 0}
    orphans = CertificateEvent.query.filter(
        CertificateEvent.organization_id == oid,
        CertificateEvent.membership_required_id.is_(None),
        CertificateEvent.event_required_id.is_(None),
    ).all()
    for ev in orphans:
        pfx = (ev.code_prefix or '').strip().upper()
        issued = Certificate.query.filter_by(certificate_event_id=int(ev.id)).count()
        if issued == 0:
            db.session.delete(ev)
            stats['deleted'] += 1
            continue
        if ev.is_active:
            ev.is_active = False
            stats['deactivated'] += 1

    for plan in MembershipPlan.query.filter_by(organization_id=oid, is_active=True):
        rows = CertificateEvent.query.filter_by(
            organization_id=oid,
            membership_required_id=int(plan.id),
            is_active=True,
        ).all()
        if len(rows) <= 1:
            continue
        plan_rows = [r for r in rows if (r.code_prefix or '').upper().startswith('PLAN-')]
        keep = plan_rows[0] if plan_rows else rows[0]
        for row in rows:
            if row.id != keep.id:
                row.is_active = False
                stats['deactivated'] += 1
    return stats


def _cleanup_legacy_certificate_event_formats(db, oid: int) -> None:
    """Alias legacy → purga completa de huérfanos."""
    _purge_orphan_certificate_event_formats(db, oid)


def seed_membership_certificate_events_for_org(db, oid: int) -> None:
    """Compat: delega al servicio central de activos de certificado."""
    from nodeone.services.certificate_assets import ensure_certificate_assets_for_org

    ensure_certificate_assets_for_org(db, int(oid), commit=True)


def run_legacy_certificate_event_cleanup(db, oid: int) -> dict:
    """Limpieza de huérfanos REL/MEM y duplicados PLAN (script o mantenimiento)."""
    stats = _purge_orphan_certificate_event_formats(db, oid)
    db.session.commit()
    return stats


def sync_membership_rows_after_paid_plan(user_id: int) -> None:
    """Al comprar un plan de pago, desactiva membresías gratuitas legacy; rige la suscripción."""
    from models.benefits import Membership
    from nodeone.core.db import db

    for mem in Membership.query.filter_by(user_id=int(user_id), is_active=True).all():
        mem.is_active = False
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()


def grant_default_basic_membership(user_id: int, organization_id: int | None = None) -> bool:
    """
    Asigna membresía básica gratuita al registrarse (idempotente).
    Devuelve True si se creó una fila nueva.
    """
    from app import User
    from models.benefits import Membership

    uid = int(user_id)
    user = User.query.get(uid)
    if user is None:
        return False

    if get_user_currently_active_membership_record(uid) is not None:
        return False

    oid = int(organization_id or getattr(user, 'organization_id', None) or 1)
    now = datetime.utcnow()
    end_date = now + timedelta(days=365)
    from nodeone.core.db import db

    db.session.add(
        Membership(
            user_id=uid,
            membership_type='basic',
            start_date=now,
            end_date=end_date,
            is_active=True,
            payment_status='paid',
            amount=0.0,
        )
    )
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return False

    try:
        seed_membership_certificate_events_for_org(db, oid)
    except Exception:
        db.session.rollback()
    return True


def _deactivate_expired_membership_rows(user_id: int) -> int:
    """Marca is_active=False en membresías vencidas (evita filas zombie)."""
    from models.benefits import Membership
    from nodeone.core.db import db

    n = 0
    for mem in Membership.query.filter_by(user_id=int(user_id), is_active=True).all():
        if not mem.is_currently_active():
            mem.is_active = False
            n += 1
    if n:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return 0
    return n


def _primary_org_id_for_user(user) -> int:
    oid = int(getattr(user, 'organization_id', None) or 0)
    if oid > 0:
        return oid
    try:
        from models.users import UserOrganization

        uo = (
            UserOrganization.query.filter_by(user_id=int(user.id), status='active')
            .order_by(UserOrganization.id.asc())
            .first()
        )
        if uo is not None:
            return int(uo.organization_id)
    except Exception:
        pass
    from utils.organization import default_organization_id

    return int(default_organization_id())


def repair_users_without_active_membership(
    *,
    organization_id: int | None = None,
    dry_run: bool = True,
) -> dict:
    """
    Usuarios activos sin membresía/suscripción vigente → membresía básica gratuita.
    Siembra certificados por plan en la(s) org(s) afectadas.
    """
    from app import SaasOrganization, User, db

    stats = {
        'users_scanned': 0,
        'expired_rows_deactivated': 0,
        'basic_granted': 0,
        'skipped_has_active': 0,
        'skipped_inactive_user': 0,
        'orgs_seeded': 0,
        'errors': 0,
    }
    orgs_to_seed: set[int] = set()

    q = User.query.order_by(User.id.asc())
    if organization_id is not None:
        q = q.filter(User.organization_id == int(organization_id))

    for user in q.all():
        stats['users_scanned'] += 1
        if not getattr(user, 'is_active', True):
            stats['skipped_inactive_user'] += 1
            continue
        if get_user_currently_active_membership_record(int(user.id)) is not None:
            stats['skipped_has_active'] += 1
            continue
        if dry_run:
            stats['basic_granted'] += 1
            orgs_to_seed.add(_primary_org_id_for_user(user))
            continue
        try:
            deactivated = _deactivate_expired_membership_rows(int(user.id))
            stats['expired_rows_deactivated'] += deactivated
            oid = _primary_org_id_for_user(user)
            if grant_default_basic_membership(int(user.id), oid):
                stats['basic_granted'] += 1
                orgs_to_seed.add(oid)
        except Exception:
            stats['errors'] += 1
            db.session.rollback()

    if not dry_run:
        if organization_id is not None:
            org_ids = {int(organization_id)}
        else:
            org_ids = {int(o.id) for o in SaasOrganization.query.filter_by(is_active=True).all()}
        org_ids |= orgs_to_seed
        for oid in sorted(org_ids):
            try:
                seed_membership_certificate_events_for_org(db, int(oid))
                stats['orgs_seeded'] += 1
            except Exception:
                stats['errors'] += 1
                db.session.rollback()

    return stats
