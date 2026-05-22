"""Análisis IA de importación (solo recomendación; no ejecuta en Odoo)."""

from __future__ import annotations

import json
import re
from typing import Any


def build_analysis_prompt(
    validation_summary: dict[str, Any],
    preview_sample: list[dict[str, Any]],
    critical_groups: list[dict[str, Any]],
) -> str:
    return (
        'Analizá esta propuesta de cambios de permisos en Odoo ERP. '
        'Respondé ÚNICAMENTE con un JSON válido (sin markdown) con estas claves:\n'
        'executive_summary (string), critical_risks (array de strings), '
        'warnings (array), recommendations (array), users_to_review (array), '
        'groups_to_review (array), safe_to_execute (boolean, solo recomendación).\n\n'
        f'Resumen validación:\n{json.dumps(validation_summary, ensure_ascii=False, indent=2)}\n\n'
        f'Grupos críticos Odoo:\n{json.dumps(critical_groups[:20], ensure_ascii=False)}\n\n'
        f'Muestra cambios propuestos:\n{json.dumps(preview_sample[:30], ensure_ascii=False)}'
    )


def parse_ai_json_response(text: str) -> dict[str, Any]:
    text = (text or '').strip()
    if not text:
        raise ValueError('Respuesta IA vacía')
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        return json.loads(m.group(0))
    raise ValueError('No se pudo extraer JSON de la respuesta IA')


def normalize_ai_result(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        'executive_summary': str(raw.get('executive_summary') or ''),
        'critical_risks': list(raw.get('critical_risks') or []),
        'warnings': list(raw.get('warnings') or []),
        'recommendations': list(raw.get('recommendations') or []),
        'users_to_review': list(raw.get('users_to_review') or []),
        'groups_to_review': list(raw.get('groups_to_review') or []),
        'safe_to_execute': bool(raw.get('safe_to_execute')),
        'disclaimer': 'safe_to_execute es solo recomendación; la aprobación humana es obligatoria.',
    }


def run_ai_analysis(
    validation_summary: dict[str, Any],
    preview_sample: list[dict[str, Any]],
    critical_groups: list[dict[str, Any]],
    *,
    session_id: str,
    organization_id: int,
) -> tuple[dict[str, Any] | None, str | None]:
    from _app.services.ai_service import ask_ai_detailed

    prompt = build_analysis_prompt(validation_summary, preview_sample, critical_groups)
    result = ask_ai_detailed(
        prompt=prompt,
        session_id=session_id,
        extra_context={'source': 'security_matrix_manager', 'phase': 1},
        organization_id=organization_id,
    )
    if not result.get('success'):
        return None, result.get('error') or 'Error IA'
    try:
        parsed = parse_ai_json_response(result.get('response') or '')
        return normalize_ai_result(parsed), None
    except Exception as e:
        return None, str(e)
