"""Guía de preparación EPosOne — checklist (no wizard lineal).

Fase 1 (negocio listo): empresa/sucursal/POS/caja/cajero (+ menú opcional).
Fase 2 (instalación): tablet vinculada → listo para abrir turno.

No endurece licencias: el motor existe pero no bloquea esta guía.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SetupTask:
    id: str
    label: str
    done: bool
    url: str
    cta: str


@dataclass(frozen=True)
class SetupGuide:
    """Estado de guía para el Dashboard."""

    phase: str  # prepare | install_device | open_shift | ready
    title: str
    subtitle: str
    tasks: tuple[SetupTask, ...]
    pending_count: int
    primary_cta_label: str | None
    primary_cta_url: str | None
    show_guide: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            'phase': self.phase,
            'title': self.title,
            'subtitle': self.subtitle,
            'tasks': [
                {
                    'id': t.id,
                    'label': t.label,
                    'done': t.done,
                    'url': t.url,
                    'cta': t.cta,
                }
                for t in self.tasks
            ],
            'pending_count': self.pending_count,
            'primary_cta_label': self.primary_cta_label,
            'primary_cta_url': self.primary_cta_url,
            'show_guide': self.show_guide,
        }


def _section(slug: str) -> str:
    from flask import url_for

    return url_for('eposone.eposone_section', slug=slug)


def build_setup_guide(organization_id: int) -> SetupGuide:
    """Calcula checklist a partir del dominio (sin flags de licenciamiento)."""
    from models.commercial_core import CorePosTerminal
    from models.core_master import CoreOrgUnit, CoreProduct
    from models.eposone_digital_menu import EposoneDigitalMenu
    from nodeone.core.master.constants import (
        ORG_UNIT_TYPE_BRANCH,
        ORG_UNIT_TYPE_POS,
        ORG_UNIT_TYPE_REGISTER,
    )
    from nodeone.modules.eposone.cashier_service import CashierService

    oid = int(organization_id)

    has_branch = (
        CoreOrgUnit.query.filter_by(organization_id=oid, unit_type=ORG_UNIT_TYPE_BRANCH)
        .filter(CoreOrgUnit.status.in_(('active', '')))
        .first()
        is not None
    )
    # También contar status active explícito o cualquier branch
    if not has_branch:
        has_branch = (
            CoreOrgUnit.query.filter_by(organization_id=oid, unit_type=ORG_UNIT_TYPE_BRANCH).first()
            is not None
        )

    has_pos = (
        CoreOrgUnit.query.filter_by(organization_id=oid, unit_type=ORG_UNIT_TYPE_POS).first()
        is not None
    )
    has_register = (
        CoreOrgUnit.query.filter_by(
            organization_id=oid, unit_type=ORG_UNIT_TYPE_REGISTER
        ).first()
        is not None
    )
    cashiers = CashierService.list_cashiers(oid, active_only=True)
    has_cashier = len(cashiers) > 0
    has_products = (
        CoreProduct.query.filter_by(organization_id=oid, status='active').first() is not None
    )
    has_digital_menu = (
        EposoneDigitalMenu.query.filter_by(organization_id=oid, active=True).first() is not None
    )
    has_device = (
        CorePosTerminal.query.filter_by(organization_id=oid).first() is not None
    )

    # Empresa: siempre "hecha" si hay org (el tenant ya existe). Checkbox informativo.
    has_company = True

    prepare_tasks = (
        SetupTask(
            'company',
            'Empresa',
            has_company,
            _section('organization'),
            'Revisar empresa',
        ),
        SetupTask(
            'branch',
            'Crear sucursal',
            has_branch,
            _section('branches'),
            'Crear sucursal',
        ),
        SetupTask(
            'pos',
            'Crear punto de venta',
            has_pos,
            _section('pos-points'),
            'Crear punto de venta',
        ),
        SetupTask(
            'register',
            'Crear caja',
            has_register,
            _section('registers'),
            'Crear caja',
        ),
        SetupTask(
            'cashier',
            'Crear cajero',
            has_cashier,
            _section('cashiers'),
            'Crear cajero',
        ),
        SetupTask(
            'products',
            'Cargar menú / productos',
            has_products,
            _section('products'),
            'Cargar productos',
        ),
        SetupTask(
            'digital_menu',
            'Publicar menú digital',
            has_digital_menu,
            _section('digital-menu'),
            'Menú digital',
        ),
    )

    # Core para operar BO (sin tablet): sucursal+POS+caja+cajero. Productos/menú son piloto Mexican Food.
    core_ready = has_branch and has_pos and has_register and has_cashier
    pending_prepare = [t for t in prepare_tasks if not t.done]
    # Para "empresa lista" exigimos core; productos/menú cuentan en checklist pero no bloquean fase install
    business_ready = core_ready

    if not business_ready:
        next_task = next((t for t in prepare_tasks if not t.done and t.id != 'company'), None)
        return SetupGuide(
            phase='prepare',
            title='Bienvenido a EPosOne',
            subtitle='Todavía no podés operar. Completá estas tareas para dejar el negocio listo.',
            tasks=prepare_tasks,
            pending_count=len(pending_prepare),
            primary_cta_label=next_task.cta if next_task else None,
            primary_cta_url=next_task.url if next_task else None,
            show_guide=True,
        )

    if not has_device:
        return SetupGuide(
            phase='install_device',
            title='Empresa lista',
            subtitle='La estructura del negocio está lista. Cuando vayas a instalar una tablet, vinculá el dispositivo.',
            tasks=prepare_tasks,
            pending_count=0,
            primary_cta_label='Instalar dispositivo',
            primary_cta_url=_section('registers') + '?install=1',
            show_guide=True,
        )

    from models.commercial_core import CoreCashShift

    has_shift_history = (
        CoreCashShift.query.filter_by(organization_id=oid).first() is not None
    )
    if has_shift_history:
        return SetupGuide(
            phase='ready',
            title='',
            subtitle='',
            tasks=prepare_tasks,
            pending_count=0,
            primary_cta_label=None,
            primary_cta_url=None,
            show_guide=False,
        )

    return SetupGuide(
        phase='open_shift',
        title='Tablet instalada',
        subtitle='Podés abrir tu primer turno y empezar a vender.',
        tasks=prepare_tasks,
        pending_count=0,
        primary_cta_label='Ir a turnos',
        primary_cta_url=_section('shifts'),
        show_guide=True,
    )
