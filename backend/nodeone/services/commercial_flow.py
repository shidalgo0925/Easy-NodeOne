"""
Resolución de flujo comercial por ítem de catálogo (Service).

Orden oficial (sincronizado con docs/commercial-products-nodeone.md):
1. COURSE
2. EXTERNAL (external_link)
3. CV_REGISTRATION
4. SERVICE_CONSULTATIVE (appointment_type_id)
5. SERVICE_INCLUDED (is_included en pricing O base_price == 0)
6. SERVICE_DIRECT
"""

from __future__ import annotations

from typing import Any, Mapping

# Valores expuestos a API/UI (persistibles en el futuro).
COMMERCIAL_FLOW_MEMBERSHIP = 'MEMBERSHIP'
COMMERCIAL_FLOW_EVENT = 'EVENT'
COMMERCIAL_FLOW_SERVICE_INCLUDED = 'SERVICE_INCLUDED'
COMMERCIAL_FLOW_SERVICE_DIRECT = 'SERVICE_DIRECT'
COMMERCIAL_FLOW_SERVICE_CONSULTATIVE = 'SERVICE_CONSULTATIVE'
COMMERCIAL_FLOW_COURSE = 'COURSE'
COMMERCIAL_FLOW_CV_REGISTRATION = 'CV_REGISTRATION'
COMMERCIAL_FLOW_EXTERNAL = 'EXTERNAL'
COMMERCIAL_FLOW_WORKSHOP_ORDER = 'WORKSHOP_ORDER'

ALL_COMMERCIAL_FLOWS = frozenset(
    {
        COMMERCIAL_FLOW_MEMBERSHIP,
        COMMERCIAL_FLOW_EVENT,
        COMMERCIAL_FLOW_SERVICE_INCLUDED,
        COMMERCIAL_FLOW_SERVICE_DIRECT,
        COMMERCIAL_FLOW_SERVICE_CONSULTATIVE,
        COMMERCIAL_FLOW_COURSE,
        COMMERCIAL_FLOW_CV_REGISTRATION,
        COMMERCIAL_FLOW_EXTERNAL,
        COMMERCIAL_FLOW_WORKSHOP_ORDER,
    }
)


def resolve_commercial_flow_type(service, pricing: Mapping[str, Any] | None) -> str:
    """
    `pricing`: resultado de ``Service.pricing_for_membership(membership_type)`` para el usuario/vista actual.

    No evaluar precio de cita (``pricing_for_appointment_booking``) aquí: solo reglas de catálogo
    e ítem de servicio, para un único CTA coherente en la ficha pública.
    """
    pricing = pricing or {}
    st = (getattr(service, 'service_type', None) or 'AGENDABLE').strip().upper()
    if st == 'COURSE':
        return COMMERCIAL_FLOW_COURSE
    if (getattr(service, 'external_link', None) or '').strip():
        return COMMERCIAL_FLOW_EXTERNAL
    if st == 'CV_REGISTRATION':
        return COMMERCIAL_FLOW_CV_REGISTRATION
    if st in ('WORKSHOP_ORDER', 'WORKSHOP'):
        return COMMERCIAL_FLOW_WORKSHOP_ORDER
    if getattr(service, 'appointment_type_id', None):
        return COMMERCIAL_FLOW_SERVICE_CONSULTATIVE
    bp = float(getattr(service, 'base_price', None) or 0.0)
    if bool(pricing.get('is_included')) or bp == 0.0:
        return COMMERCIAL_FLOW_SERVICE_INCLUDED
    return COMMERCIAL_FLOW_SERVICE_DIRECT


def flow_type_badge_label(flow: str) -> str:
    return {
        COMMERCIAL_FLOW_SERVICE_INCLUDED: 'Incluido',
        COMMERCIAL_FLOW_SERVICE_DIRECT: 'Compra directa',
        COMMERCIAL_FLOW_SERVICE_CONSULTATIVE: 'Con cita',
        COMMERCIAL_FLOW_COURSE: 'Curso',
        COMMERCIAL_FLOW_CV_REGISTRATION: 'Hoja de vida',
        COMMERCIAL_FLOW_EXTERNAL: 'Enlace externo',
        COMMERCIAL_FLOW_WORKSHOP_ORDER: 'Taller / pedido',
        COMMERCIAL_FLOW_MEMBERSHIP: 'Membresía',
        COMMERCIAL_FLOW_EVENT: 'Evento',
    }.get(flow, flow)


def flow_cta_labels(flow: str) -> tuple[str, str]:
    """(label_botón, pista corta bajo el botón)."""
    return {
        COMMERCIAL_FLOW_SERVICE_INCLUDED: ('Acceder', 'Incluido en tu plan: usá el servicio sin pasar por caja.'),
        COMMERCIAL_FLOW_SERVICE_DIRECT: ('Comprar', 'Se agrega al carrito con el precio de tu plan.'),
        COMMERCIAL_FLOW_SERVICE_CONSULTATIVE: (
            'Solicitar cita gratuita',
            'Primera cita en agenda: diagnóstico; el precio final puede acordarse en cotización.',
        ),
        COMMERCIAL_FLOW_COURSE: ('Ver convocatoria', 'Matrícula y pago en la página del programa.'),
        COMMERCIAL_FLOW_CV_REGISTRATION: ('Registrar hoja de vida', 'Formulario público; no requiere iniciar sesión.'),
        COMMERCIAL_FLOW_EXTERNAL: ('Ir al enlace', 'Continuás en el sitio o recurso indicado.'),
        COMMERCIAL_FLOW_WORKSHOP_ORDER: ('Solicitar evaluación', 'Flujo de taller u orden especial.'),
        COMMERCIAL_FLOW_MEMBERSHIP: ('Elegir plan', ''),
        COMMERCIAL_FLOW_EVENT: ('Inscribirse', ''),
    }.get(flow, ('Ver detalle', ''))
