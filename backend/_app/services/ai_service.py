"""Servicio de IA configurable desde la base de datos."""

import requests


def ask_ai_detailed(prompt, session_id, extra_context=None, organization_id=None):
    """Consultar la API de IA y devolver resultado estructurado."""
    from app import AIConfig

    cfg = AIConfig.get_active_config(organization_id=organization_id)
    if not cfg or not cfg.enabled:
        return {'success': False, 'error': 'La IA está desactivada.'}

    payload = {
        'prompt': prompt,
        'session': session_id,
        'collection': cfg.collection or 'nodeone',
    }
    if extra_context:
        payload['context'] = extra_context

    headers = {'Content-Type': 'application/json'}
    if cfg.api_key:
        headers['x-api-key'] = cfg.api_key

    try:
        response = requests.post(
            cfg.api_url,
            json=payload,
            headers=headers,
            timeout=cfg.timeout_seconds or 30,
        )
        try:
            data = response.json() if response.content else {}
        except Exception:
            data = {}

        if not response.ok:
            return {
                'success': False,
                'status_code': response.status_code,
                'error': data.get('detail') or data.get('error') or data.get('message') or f'HTTP {response.status_code}',
            }

        reply = data.get('response') or data.get('answer') or data.get('message')
        if not reply:
            return {'success': False, 'status_code': response.status_code, 'error': 'La IA no devolvió contenido.'}

        return {'success': True, 'response': reply, 'status_code': response.status_code}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Timeout al consultar la IA.'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'No se pudo conectar con la API de IA.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def ask_ai(prompt, session_id, extra_context=None, organization_id=None):
    """Consultar la API de IA. Devuelve solo texto o None para compatibilidad."""
    result = ask_ai_detailed(
        prompt, session_id, extra_context=extra_context, organization_id=organization_id
    )
    return result.get('response') if result.get('success') else None
