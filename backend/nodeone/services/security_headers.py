"""Cabeceras HTTP de endurecimiento (CSP, HSTS, anti-clickjacking, etc.).

Se aplican vía ``after_request`` para que existan aunque Nginx no las añada.
Desactivar solo en entornos muy especiales: NODEONE_DISABLE_APP_SECURITY_HEADERS=1

CSP: misma política que antes en ``base.html`` (meta), ahora solo por cabecera
para evitar duplicados y cumplir auditorías que miran headers HTTP.
"""

from __future__ import annotations

import os

from flask import has_request_context, request

# Misma política que el meta CSP retirado de base.html (pasarelas de pago + CDNs).
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "worker-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
    "https://js.stripe.com https://www.paypal.com https://www.sandbox.paypal.com https://static.cloudflareinsights.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https:; "
    "font-src 'self' data: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
    "connect-src 'self' https://api.stripe.com https://merchant-ui-api.stripe.com "
    "https://api-m.paypal.com https://api-m.sandbox.paypal.com https://www.paypal.com https://www.sandbox.paypal.com "
    "https://api.cybersource.com https://api.yappy.im https://cdn.jsdelivr.net; "
    "frame-src 'self' https://*.easynodeone.com http://*.easynodeone.com https://js.stripe.com https://hooks.stripe.com "
    "https://www.paypal.com https://www.sandbox.paypal.com; "
    "object-src 'none'; base-uri 'self'; "
    "form-action 'self' https://www.paypal.com https://www.sandbox.paypal.com; "
    "upgrade-insecure-requests;"
)


def _security_headers_disabled() -> bool:
    return os.environ.get('NODEONE_DISABLE_APP_SECURITY_HEADERS', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _request_is_https(req) -> bool:
    if getattr(req, 'is_secure', False):
        return True
    return (req.headers.get('X-Forwarded-Proto') or '').strip().lower() == 'https'


def init_security_headers(app) -> None:
    """Registra after_request con cabeceras de seguridad en todas las respuestas."""

    @app.after_request
    def _inject_security_headers(response):
        if _security_headers_disabled():
            return response
        if getattr(response, 'direct_passthrough', False):
            return response
        if not has_request_context():
            return response

        # No pisar si ya vienen (p. ej. Nginx u otra capa)
        def _set(name: str, value: str) -> None:
            if name not in response.headers:
                response.headers[name] = value

        _set('X-Frame-Options', 'SAMEORIGIN')
        _set('X-Content-Type-Options', 'nosniff')
        _set('Referrer-Policy', 'strict-origin-when-cross-origin')
        _set(
            'Permissions-Policy',
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), '
            'payment=(self), usb=()',
        )
        _set('Content-Security-Policy', CONTENT_SECURITY_POLICY)

        if _request_is_https(request):
            _set(
                'Strict-Transport-Security',
                'max-age=31536000; includeSubDomains',
            )

        return response
