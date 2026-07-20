"""Motor de Políticas Comerciales — infra genérica versionada (V6).

No contiene lógica fiscal/propinas/pagos/totales. Solo identidad, versiones,
ciclo de publicación, validación pre-publish, auditoría, asignación por
alcance, herencia y snapshot para sync/bootstrap.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from models.eposone_commercial_policy import (
    EposoneCommercialPoliciesSyncState,
    EposoneCommercialPolicy,
    EposoneCommercialPolicyAssignment,
    EposoneCommercialPolicyVersion,
)

POLICY_TYPES = frozenset(
    {
        'fiscal',
        'tips',
        'payments',
        'receipt',
        'commercial_config',
        'promotion',
    }
)

SCOPE_TYPES = frozenset({'organization', 'branch', 'pos', 'register'})

PUBLICATION_STATUSES = frozenset({'draft', 'active', 'obsolete', 'archived'})

# Más específico primero (herencia / override).
SCOPE_RESOLUTION_ORDER = ('register', 'pos', 'branch', 'organization')

# Claves de porcentaje genéricas en payload (extensible por tipo).
_PERCENT_KEYS = frozenset(
    {
        'percent',
        'rate',
        'percentage',
        'tip_percent',
        'tax_percent',
        'discount_percent',
        'default_percent',
    }
)


class CommercialPolicyValidationError(ValueError):
    pass


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec='milliseconds') + ('Z' if value.tzinfo is None else '')


def _parse_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _audit(organization_id: int, event_type: str, payload: dict[str, Any]) -> None:
    try:
        from nodeone.core.services.audit import AuditService

        AuditService.publish_domain_event(
            int(organization_id),
            event_type,
            payload,
            source_app_id='eposone',
        )
    except Exception:
        pass


def resolve_scope_chain(
    *,
    organization_id: int,
    branch_ref: str | None = None,
    pos_ref: str | None = None,
    register_ref: str | None = None,
) -> list[tuple[str, str]]:
    """Cadena de scopes de más específico a más general."""
    chain: list[tuple[str, str]] = []
    if register_ref:
        chain.append(('register', str(register_ref).strip()))
    if pos_ref:
        chain.append(('pos', str(pos_ref).strip()))
    if branch_ref:
        chain.append(('branch', str(branch_ref).strip()))
    chain.append(('organization', str(int(organization_id))))
    return chain


def validate_policy_payload(
    policy_type: str,
    payload: dict[str, Any] | None,
    *,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> None:
    """Validaciones genéricas antes de publicar. Extensible por tipo."""
    ptype = str(policy_type or '').strip().lower()
    if ptype not in POLICY_TYPES:
        raise CommercialPolicyValidationError(f'policy_type_invalid:{ptype}')

    if valid_from and valid_to and valid_from > valid_to:
        raise CommercialPolicyValidationError('valid_from_after_valid_to')

    data = payload if isinstance(payload, dict) else {}

    def _walk(obj: Any, path: str = '') -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                key_l = str(key).lower()
                child = f'{path}.{key_l}' if path else key_l
                if key_l in _PERCENT_KEYS or key_l.endswith('_percent') or key_l.endswith('_rate'):
                    try:
                        num = float(val)
                    except (TypeError, ValueError) as exc:
                        raise CommercialPolicyValidationError(
                            f'percent_invalid:{child}'
                        ) from exc
                    # Acepta 0–100 o 0–1 (fracción).
                    if not (0.0 <= num <= 100.0):
                        raise CommercialPolicyValidationError(f'percent_out_of_range:{child}')
                _walk(val, child)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f'{path}[{i}]')

    _walk(data)

    # Fechas embebidas en payload (ISO) si existen.
    for key in ('valid_from', 'valid_to', 'starts_at', 'ends_at'):
        raw = data.get(key)
        if raw is None or raw == '':
            continue
        if not isinstance(raw, str):
            raise CommercialPolicyValidationError(f'date_invalid:{key}')
        try:
            datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError as exc:
            raise CommercialPolicyValidationError(f'date_invalid:{key}') from exc

    pf = data.get('valid_from') or data.get('starts_at')
    pt = data.get('valid_to') or data.get('ends_at')
    if isinstance(pf, str) and isinstance(pt, str) and pf and pt:
        try:
            df = datetime.fromisoformat(pf.replace('Z', '+00:00'))
            dt = datetime.fromisoformat(pt.replace('Z', '+00:00'))
            if df > dt:
                raise CommercialPolicyValidationError('payload_valid_from_after_valid_to')
        except CommercialPolicyValidationError:
            raise
        except ValueError:
            pass


class CommercialPolicyService:
    @staticmethod
    def get_policies_version(organization_id: int) -> int:
        row = EposoneCommercialPoliciesSyncState.query.filter_by(
            organization_id=int(organization_id)
        ).first()
        if row is None:
            return 0
        return int(row.policies_version or 0)

    @staticmethod
    def bump_policies_version(organization_id: int) -> int:
        from app import db

        oid = int(organization_id)
        row = EposoneCommercialPoliciesSyncState.query.filter_by(organization_id=oid).first()
        now = datetime.utcnow()
        if row is None:
            row = EposoneCommercialPoliciesSyncState(
                organization_id=oid,
                policies_version=1,
                updated_at=now,
            )
            db.session.add(row)
        else:
            row.policies_version = int(row.policies_version or 0) + 1
            row.updated_at = now
        db.session.flush()
        return int(row.policies_version)

    @staticmethod
    def create_policy(
        organization_id: int,
        *,
        policy_type: str,
        code: str,
        name: str,
        payload: dict[str, Any] | None = None,
        active: bool = True,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        created_by_user_id: int | None = None,
        assign_organization_scope: bool = True,
        publish: bool = False,
    ) -> dict[str, Any]:
        """Crea política + versión 1 en draft (o publica si publish=True)."""
        from app import db

        ptype = str(policy_type or '').strip().lower()
        if ptype not in POLICY_TYPES:
            raise CommercialPolicyValidationError(f'policy_type_invalid:{ptype}')
        code_n = str(code or '').strip()
        name_n = str(name or '').strip()
        if not code_n or not name_n:
            raise CommercialPolicyValidationError('code_and_name_required')
        if valid_from and valid_to and valid_from > valid_to:
            raise CommercialPolicyValidationError('valid_from_after_valid_to')

        oid = int(organization_id)
        existing = EposoneCommercialPolicy.query.filter_by(
            organization_id=oid, policy_type=ptype, code=code_n
        ).first()
        if existing is not None:
            raise CommercialPolicyValidationError('policy_code_exists')

        now = datetime.utcnow()
        policy = EposoneCommercialPolicy(
            organization_id=oid,
            policy_type=ptype,
            code=code_n,
            name=name_n,
            active=bool(active),
            valid_from=valid_from,
            valid_to=valid_to,
            created_at=now,
            updated_at=now,
        )
        db.session.add(policy)
        db.session.flush()

        version = EposoneCommercialPolicyVersion(
            organization_id=oid,
            policy_id=int(policy.id),
            version_number=1,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
            publication_status='draft',
            is_current=False,
            created_at=now,
            created_by_user_id=created_by_user_id,
            published_at=None,
        )
        db.session.add(version)
        db.session.flush()

        if assign_organization_scope:
            CommercialPolicyService.assign(
                oid,
                policy_type=ptype,
                policy_id=int(policy.id),
                scope_type='organization',
                scope_ref=str(oid),
                policy_version_id=None,
                bump=False,
                audit=False,
            )

        _audit(
            oid,
            'eposone.commercial_policy.created',
            {
                'policy_id': int(policy.id),
                'policy_type': ptype,
                'code': code_n,
                'version_id': int(version.id),
                'publication_status': 'draft',
            },
        )

        if publish:
            CommercialPolicyService._activate_version(
                policy, version, bump=False, created_by_user_id=created_by_user_id
            )

        CommercialPolicyService.bump_policies_version(oid)
        db.session.commit()
        db.session.refresh(version)
        return CommercialPolicyService.policy_to_dict(policy, version)

    @staticmethod
    def create_draft_version(
        organization_id: int,
        policy_id: int,
        payload: dict[str, Any] | None = None,
        *,
        created_by_user_id: int | None = None,
    ) -> dict[str, Any]:
        """Nueva versión en draft — no disponible para POS hasta publish."""
        from app import db

        oid = int(organization_id)
        policy = EposoneCommercialPolicy.query.filter_by(
            organization_id=oid, id=int(policy_id)
        ).first()
        if policy is None:
            raise CommercialPolicyValidationError('policy_not_found')

        latest = (
            EposoneCommercialPolicyVersion.query.filter_by(policy_id=int(policy.id))
            .order_by(EposoneCommercialPolicyVersion.version_number.desc())
            .first()
        )
        next_n = int(latest.version_number if latest else 0) + 1
        now = datetime.utcnow()
        version = EposoneCommercialPolicyVersion(
            organization_id=oid,
            policy_id=int(policy.id),
            version_number=next_n,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
            publication_status='draft',
            is_current=False,
            created_at=now,
            created_by_user_id=created_by_user_id,
            published_at=None,
        )
        db.session.add(version)
        policy.updated_at = now
        db.session.flush()
        _audit(
            oid,
            'eposone.commercial_policy.version_created',
            {
                'policy_id': int(policy.id),
                'version_id': int(version.id),
                'version_number': next_n,
                'publication_status': 'draft',
            },
        )
        CommercialPolicyService.bump_policies_version(oid)
        db.session.commit()
        return CommercialPolicyService.policy_to_dict(policy, version)

    @staticmethod
    def publish_version(
        organization_id: int,
        policy_id: int,
        *,
        version_id: int | None = None,
        payload: dict[str, Any] | None = None,
        created_by_user_id: int | None = None,
    ) -> dict[str, Any]:
        """Valida y publica una versión draft (o crea draft+publish si hay payload)."""
        from app import db

        oid = int(organization_id)
        policy = EposoneCommercialPolicy.query.filter_by(
            organization_id=oid, id=int(policy_id)
        ).first()
        if policy is None:
            raise CommercialPolicyValidationError('policy_not_found')

        version: EposoneCommercialPolicyVersion | None = None
        if version_id is not None:
            version = EposoneCommercialPolicyVersion.query.filter_by(
                organization_id=oid,
                policy_id=int(policy.id),
                id=int(version_id),
            ).first()
            if version is None:
                raise CommercialPolicyValidationError('policy_version_not_found')
            if payload is not None:
                version.payload_json = json.dumps(
                    payload, ensure_ascii=False, sort_keys=True
                )
        elif payload is not None:
            latest = (
                EposoneCommercialPolicyVersion.query.filter_by(policy_id=int(policy.id))
                .order_by(EposoneCommercialPolicyVersion.version_number.desc())
                .first()
            )
            next_n = int(latest.version_number if latest else 0) + 1
            now = datetime.utcnow()
            version = EposoneCommercialPolicyVersion(
                organization_id=oid,
                policy_id=int(policy.id),
                version_number=next_n,
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                publication_status='draft',
                is_current=False,
                created_at=now,
                created_by_user_id=created_by_user_id,
                published_at=None,
            )
            db.session.add(version)
            db.session.flush()
            _audit(
                oid,
                'eposone.commercial_policy.version_created',
                {
                    'policy_id': int(policy.id),
                    'version_id': int(version.id),
                    'version_number': next_n,
                    'publication_status': 'draft',
                },
            )
        else:
            version = (
                EposoneCommercialPolicyVersion.query.filter_by(
                    policy_id=int(policy.id), publication_status='draft'
                )
                .order_by(EposoneCommercialPolicyVersion.version_number.desc())
                .first()
            )
            if version is None:
                raise CommercialPolicyValidationError('no_draft_to_publish')

        CommercialPolicyService._activate_version(
            policy, version, bump=True, created_by_user_id=created_by_user_id
        )
        db.session.commit()
        db.session.refresh(version)
        return CommercialPolicyService.policy_to_dict(policy, version)

    @staticmethod
    def _activate_version(
        policy: EposoneCommercialPolicy,
        version: EposoneCommercialPolicyVersion,
        *,
        bump: bool,
        created_by_user_id: int | None = None,
    ) -> None:
        status = str(version.publication_status or 'draft')
        if status == 'archived':
            raise CommercialPolicyValidationError('cannot_publish_archived')
        if status == 'obsolete':
            raise CommercialPolicyValidationError('cannot_publish_obsolete')

        payload = _parse_payload(version.payload_json)
        validate_policy_payload(
            str(policy.policy_type),
            payload,
            valid_from=policy.valid_from,
            valid_to=policy.valid_to,
        )
        CommercialPolicyService._validate_assignment_refs(int(policy.organization_id), policy)

        now = datetime.utcnow()
        # Versión active previa → obsolete
        prev_active = EposoneCommercialPolicyVersion.query.filter_by(
            policy_id=int(policy.id), publication_status='active'
        ).all()
        for prev in prev_active:
            if int(prev.id) == int(version.id):
                continue
            prev.publication_status = 'obsolete'
            prev.is_current = False

        version.publication_status = 'active'
        version.is_current = True
        version.published_at = now
        if created_by_user_id is not None:
            version.created_by_user_id = created_by_user_id
        policy.updated_at = now

        _audit(
            int(policy.organization_id),
            'eposone.commercial_policy.version_published',
            {
                'policy_id': int(policy.id),
                'version_id': int(version.id),
                'version_number': int(version.version_number),
                'publication_status': 'active',
                'policy_type': str(policy.policy_type),
                'code': str(policy.code),
            },
        )
        if bump:
            CommercialPolicyService.bump_policies_version(int(policy.organization_id))

    @staticmethod
    def _validate_assignment_refs(
        organization_id: int, policy: EposoneCommercialPolicy
    ) -> None:
        """Detecta asignaciones huérfanas / refs vacías para esta política."""
        rows = EposoneCommercialPolicyAssignment.query.filter_by(
            organization_id=int(organization_id),
            policy_id=int(policy.id),
            active=True,
        ).all()
        for row in rows:
            if not str(row.scope_ref or '').strip():
                raise CommercialPolicyValidationError(
                    f'assignment_scope_ref_missing:{row.id}'
                )
            if row.policy_version_id is not None:
                ver = EposoneCommercialPolicyVersion.query.filter_by(
                    id=int(row.policy_version_id), policy_id=int(policy.id)
                ).first()
                if ver is None:
                    raise CommercialPolicyValidationError(
                        f'assignment_version_missing:{row.id}'
                    )

    @staticmethod
    def set_policy_active(
        organization_id: int, policy_id: int, *, active: bool
    ) -> dict[str, Any]:
        from app import db

        oid = int(organization_id)
        policy = EposoneCommercialPolicy.query.filter_by(
            organization_id=oid, id=int(policy_id)
        ).first()
        if policy is None:
            raise CommercialPolicyValidationError('policy_not_found')
        policy.active = bool(active)
        policy.updated_at = datetime.utcnow()
        event = (
            'eposone.commercial_policy.activated'
            if active
            else 'eposone.commercial_policy.deactivated'
        )
        _audit(
            oid,
            event,
            {'policy_id': int(policy.id), 'code': str(policy.code), 'active': bool(active)},
        )
        CommercialPolicyService.bump_policies_version(oid)
        db.session.commit()
        return CommercialPolicyService.policy_to_dict(policy)

    @staticmethod
    def archive_version(
        organization_id: int, policy_id: int, version_id: int
    ) -> dict[str, Any]:
        from app import db

        oid = int(organization_id)
        version = EposoneCommercialPolicyVersion.query.filter_by(
            organization_id=oid, policy_id=int(policy_id), id=int(version_id)
        ).first()
        if version is None:
            raise CommercialPolicyValidationError('policy_version_not_found')
        if str(version.publication_status) == 'active':
            raise CommercialPolicyValidationError('cannot_archive_active_publish_first')
        version.publication_status = 'archived'
        version.is_current = False
        policy = EposoneCommercialPolicy.query.filter_by(id=int(policy_id)).first()
        if policy is not None:
            policy.updated_at = datetime.utcnow()
        _audit(
            oid,
            'eposone.commercial_policy.version_archived',
            {
                'policy_id': int(policy_id),
                'version_id': int(version.id),
                'version_number': int(version.version_number),
            },
        )
        CommercialPolicyService.bump_policies_version(oid)
        db.session.commit()
        return CommercialPolicyService.policy_to_dict(policy, version) if policy else {
            'policy_version_id': int(version.id),
            'publication_status': 'archived',
        }

    @staticmethod
    def assign(
        organization_id: int,
        *,
        policy_type: str,
        policy_id: int,
        scope_type: str,
        scope_ref: str,
        policy_version_id: int | None = None,
        active: bool = True,
        bump: bool = True,
        audit: bool = True,
    ) -> dict[str, Any]:
        from app import db

        oid = int(organization_id)
        ptype = str(policy_type or '').strip().lower()
        stype = str(scope_type or '').strip().lower()
        sref = str(scope_ref or '').strip()
        if ptype not in POLICY_TYPES:
            raise CommercialPolicyValidationError(f'policy_type_invalid:{ptype}')
        if stype not in SCOPE_TYPES:
            raise CommercialPolicyValidationError(f'scope_type_invalid:{stype}')
        if not sref:
            raise CommercialPolicyValidationError('scope_ref_required')

        policy = EposoneCommercialPolicy.query.filter_by(
            organization_id=oid, id=int(policy_id), policy_type=ptype
        ).first()
        if policy is None:
            raise CommercialPolicyValidationError('policy_not_found')

        if policy_version_id is not None:
            ver = EposoneCommercialPolicyVersion.query.filter_by(
                organization_id=oid,
                policy_id=int(policy.id),
                id=int(policy_version_id),
            ).first()
            if ver is None:
                raise CommercialPolicyValidationError('policy_version_not_found')
            if str(ver.publication_status) == 'archived':
                raise CommercialPolicyValidationError('cannot_assign_archived_version')

        now = datetime.utcnow()
        row = EposoneCommercialPolicyAssignment.query.filter_by(
            organization_id=oid,
            policy_type=ptype,
            scope_type=stype,
            scope_ref=sref,
        ).first()
        created = row is None
        if row is None:
            row = EposoneCommercialPolicyAssignment(
                organization_id=oid,
                policy_type=ptype,
                policy_id=int(policy.id),
                policy_version_id=policy_version_id,
                scope_type=stype,
                scope_ref=sref,
                active=bool(active),
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
        else:
            # Conflicto tipado: reemplazo explícito de asignación mismo scope/tipo.
            row.policy_id = int(policy.id)
            row.policy_version_id = policy_version_id
            row.active = bool(active)
            row.updated_at = now

        if audit:
            _audit(
                oid,
                'eposone.commercial_policy.assigned',
                {
                    'policy_id': int(policy.id),
                    'policy_type': ptype,
                    'scope_type': stype,
                    'scope_ref': sref,
                    'created': created,
                    'active': bool(active),
                },
            )

        if bump:
            CommercialPolicyService.bump_policies_version(oid)
            db.session.commit()
        else:
            db.session.flush()

        return {
            'id': int(row.id) if row.id else None,
            'policy_type': ptype,
            'policy_id': int(policy.id),
            'policy_version_id': int(policy_version_id) if policy_version_id else None,
            'scope_type': stype,
            'scope_ref': sref,
            'active': bool(row.active),
        }

    @staticmethod
    def policy_to_dict(
        policy: EposoneCommercialPolicy | None,
        version: EposoneCommercialPolicyVersion | None = None,
    ) -> dict[str, Any]:
        if policy is None:
            return {}
        if version is None:
            version = EposoneCommercialPolicyVersion.query.filter_by(
                policy_id=int(policy.id), publication_status='active', is_current=True
            ).first()
            if version is None:
                version = (
                    EposoneCommercialPolicyVersion.query.filter_by(policy_id=int(policy.id))
                    .order_by(EposoneCommercialPolicyVersion.version_number.desc())
                    .first()
                )
        return {
            'policy_id': int(policy.id),
            'organization_id': int(policy.organization_id),
            'policy_type': str(policy.policy_type),
            'code': str(policy.code),
            'name': str(policy.name),
            'active': bool(policy.active),
            'valid_from': _iso_utc(policy.valid_from),
            'valid_to': _iso_utc(policy.valid_to),
            'version_number': int(version.version_number) if version else None,
            'policy_version_id': int(version.id) if version else None,
            'publication_status': (
                str(version.publication_status) if version else None
            ),
            'payload': _parse_payload(version.payload_json if version else None),
            'published_at': _iso_utc(version.published_at) if version else None,
            'updated_at': _iso_utc(policy.updated_at),
        }

    @staticmethod
    def resolve_effective_bundles(
        organization_id: int,
        *,
        branch_ref: str | None = None,
        pos_ref: str | None = None,
        register_ref: str | None = None,
        at: datetime | None = None,
    ) -> dict[str, dict[str, Any] | None]:
        """Solo versiones publication_status=active llegan al POS."""
        oid = int(organization_id)
        when = at or datetime.utcnow()
        chain = resolve_scope_chain(
            organization_id=oid,
            branch_ref=branch_ref,
            pos_ref=pos_ref,
            register_ref=register_ref,
        )
        assignments = (
            EposoneCommercialPolicyAssignment.query.filter_by(
                organization_id=oid, active=True
            ).all()
        )
        by_scope: dict[tuple[str, str, str], EposoneCommercialPolicyAssignment] = {}
        for a in assignments:
            by_scope[(str(a.policy_type), str(a.scope_type), str(a.scope_ref))] = a

        bundles: dict[str, dict[str, Any] | None] = {t: None for t in sorted(POLICY_TYPES)}
        for ptype in POLICY_TYPES:
            chosen: EposoneCommercialPolicyAssignment | None = None
            for scope_type, scope_ref in chain:
                key = (ptype, scope_type, scope_ref)
                if key in by_scope:
                    chosen = by_scope[key]
                    break
            if chosen is None:
                continue
            policy = EposoneCommercialPolicy.query.filter_by(
                organization_id=oid, id=int(chosen.policy_id)
            ).first()
            if policy is None or not bool(policy.active):
                continue
            if policy.valid_from and policy.valid_from > when:
                continue
            if policy.valid_to and policy.valid_to < when:
                continue
            version = None
            if chosen.policy_version_id:
                version = EposoneCommercialPolicyVersion.query.filter_by(
                    id=int(chosen.policy_version_id),
                    policy_id=int(policy.id),
                    publication_status='active',
                ).first()
            if version is None:
                version = EposoneCommercialPolicyVersion.query.filter_by(
                    policy_id=int(policy.id),
                    publication_status='active',
                    is_current=True,
                ).first()
            if version is None:
                continue
            data = CommercialPolicyService.policy_to_dict(policy, version)
            data['resolved_scope_type'] = str(chosen.scope_type)
            data['resolved_scope_ref'] = str(chosen.scope_ref)
            bundles[ptype] = data
        return bundles

    @staticmethod
    def snapshot_for_terminal(
        organization_id: int,
        *,
        branch_ref: str | None = None,
        pos_ref: str | None = None,
        register_ref: str | None = None,
        known_policies_version: int | None = None,
    ) -> dict[str, Any]:
        """Payload bootstrap/sync: incremental por policies_version."""
        oid = int(organization_id)
        version = CommercialPolicyService.get_policies_version(oid)
        unchanged = (
            known_policies_version is not None and int(known_policies_version) == version
        )
        out: dict[str, Any] = {
            'policies_version': version,
            'policies_changed': not unchanged,
        }
        if unchanged:
            return out

        bundles = CommercialPolicyService.resolve_effective_bundles(
            oid,
            branch_ref=branch_ref,
            pos_ref=pos_ref,
            register_ref=register_ref,
        )
        policies_list = [b for b in bundles.values() if b is not None]
        out['commercial_policies'] = policies_list
        out['commercial_policies_count'] = len(policies_list)
        out['policy_bundles'] = bundles
        out['register_commercial_config'] = (bundles.get('commercial_config') or {}).get(
            'payload'
        ) or {}
        out['fiscal_config'] = (bundles.get('fiscal') or {}).get('payload') or {}
        out['tips_config'] = (bundles.get('tips') or {}).get('payload') or {}
        out['payments_config'] = (bundles.get('payments') or {}).get('payload') or {}
        out['receipt_config'] = (bundles.get('receipt') or {}).get('payload') or {}
        _audit(
            oid,
            'eposone.commercial_policy.synced',
            {
                'policies_version': version,
                'policies_changed': True,
                'count': len(policies_list),
                'branch_ref': branch_ref,
                'pos_ref': pos_ref,
                'register_ref': register_ref,
            },
        )
        return out
