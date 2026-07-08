"""App Registry declarativo — fuente de metadatos para Launcher y licenciamiento (Etapa 2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ApplicationDescriptor:
    id: str
    name: str
    saas_codes: tuple[str, ...]
    depends_on: tuple[str, ...] = ()
    integration_order: int | None = None
    native_platform: bool = False
    is_shared_service: bool = False


# Catálogo alineado con docs/EN1_PLATFORM_ETAPA1_CORE_APPS.md
APPLICATIONS: tuple[ApplicationDescriptor, ...] = (
    ApplicationDescriptor(
        id='contacts',
        name='Contactos (Core)',
        saas_codes=('contacts', 'crm_contacts'),
        is_shared_service=True,
    ),
    ApplicationDescriptor(
        id='emembership',
        name='EMembership',
        saas_codes=('memberships',),
        integration_order=1,
    ),
    ApplicationDescriptor(
        id='ecrm',
        name='ECRM',
        saas_codes=('crm',),
        depends_on=('contacts',),
        integration_order=2,
    ),
    ApplicationDescriptor(
        id='eevents',
        name='EEvents',
        saas_codes=('events',),
        depends_on=('contacts',),
        integration_order=3,
    ),
    ApplicationDescriptor(
        id='ecertificates',
        name='ECertificates',
        saas_codes=('certificates',),
        depends_on=('eevents', 'emembership'),
        integration_order=4,
    ),
    ApplicationDescriptor(
        id='eappointments',
        name='EAppointments',
        saas_codes=('appointments',),
        integration_order=5,
    ),
    ApplicationDescriptor(
        id='academic',
        name='Academic / LMS',
        saas_codes=('academic',),
        depends_on=('emembership',),
    ),
    ApplicationDescriptor(
        id='eposone',
        name='EPosOne',
        saas_codes=('eposone',),
        depends_on=('contacts',),
        native_platform=True,
    ),
    ApplicationDescriptor(
        id='esales',
        name='Ventas',
        saas_codes=('sales',),
        depends_on=('contacts',),
    ),
    ApplicationDescriptor(
        id='efactura',
        name='EFactura',
        saas_codes=('efactura',),
        depends_on=('contacts', 'esales'),
    ),
    ApplicationDescriptor(
        id='emarketing',
        name='EMarketing',
        saas_codes=('marketing_email',),
        depends_on=('ecommunications',),
    ),
    ApplicationDescriptor(
        id='ecommunications',
        name='Comunicaciones',
        saas_codes=('communications',),
    ),
    ApplicationDescriptor(
        id='eanalytics',
        name='Analítica',
        saas_codes=('analytics',),
    ),
)


def list_applications(*, include_shared: bool = True) -> Sequence[ApplicationDescriptor]:
    if include_shared:
        return APPLICATIONS
    return tuple(a for a in APPLICATIONS if not a.is_shared_service)


def get_application(app_id: str) -> ApplicationDescriptor | None:
    key = (app_id or '').strip().lower()
    for app in APPLICATIONS:
        if app.id == key:
            return app
    return None
