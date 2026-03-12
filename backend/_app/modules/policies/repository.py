# Acceso a datos de políticas.
from app import Policy, PolicyAcceptance


def get_policy_by_slug(slug, active_only=True):
    q = Policy.query.filter_by(slug=slug)
    if active_only:
        q = q.filter_by(is_active=True)
    return q.first()


def get_policy_by_id(policy_id):
    return Policy.query.get(policy_id)


def user_has_accepted_policy(user_id, policy):
    if not policy:
        return False
    return PolicyAcceptance.query.filter_by(
        user_id=user_id,
        policy_id=policy.id,
    ).first() is not None


def record_acceptance(user_id, policy_id, version, ip_address=None):
    from app import db
    from datetime import datetime
    acc = PolicyAcceptance(
        user_id=user_id,
        policy_id=policy_id,
        version=version,
        ip_address=ip_address,
    )
    db.session.add(acc)
    db.session.commit()
    return acc


def get_acceptances_for_policy(policy_id):
    return PolicyAcceptance.query.filter_by(policy_id=policy_id).order_by(
        PolicyAcceptance.accepted_at.desc()
    ).all()
