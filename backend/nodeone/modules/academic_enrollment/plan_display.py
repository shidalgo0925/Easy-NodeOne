"""Textos de tarjetas de plan en landing /inscripcion (un cargo = total del plan)."""

from __future__ import annotations


def plan_card_display(plan, program) -> dict[str, str]:
    """
    Líneas para la UI pública. IIUS cobra un solo monto en checkout;
    «6/10 cuotas» son modalidades de precio total, no débitos mensuales.
    """
    code = (getattr(plan, 'code', None) or '').strip().lower()
    currency = (getattr(plan, 'currency', None) or getattr(program, 'currency', None) or 'USD').strip().upper()
    total = int(getattr(plan, 'total_amount_cents', 0) or 0) / 100.0
    n = getattr(plan, 'installment_count', None)
    inst = getattr(plan, 'installment_amount', None)

    if code == 'full' or not n:
        disc = (getattr(plan, 'discount_label', None) or '').strip()
        return {
            'badge': 'Mejor precio',
            'primary': 'Un solo pago en el checkout',
            'secondary': disc or 'Incluye 20% de descuento sobre el plan financiado',
        }

    try:
        n_int = int(n)
    except (TypeError, ValueError):
        n_int = 0
    if not inst and n_int > 0 and total > 0:
        inst = round(total / n_int)

    inst_txt = f'{int(round(inst)):,}'.replace(',', '.') if inst else '—'
    total_txt = f'{int(round(total)):,}'.replace(',', '.')

    return {
        'badge': f'Plan {n_int} cuotas',
        'primary': f'Un pago hoy: {currency} {total_txt} (total del programa)',
        'secondary': (
            f'Referencia: {n_int} × {currency} {inst_txt}. '
            'No son cargos automáticos cada mes; pagás el total acordado en una sola transacción.'
        ),
    }
