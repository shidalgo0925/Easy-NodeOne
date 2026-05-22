#!/usr/bin/env python3
"""Comprueba si PayPal live está listo (org 1 / IIUS). No imprime secretos."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app import app
    from nodeone.services.payment_config_provision import dedicated_active_config

    ok = True
    with app.app_context():
        cfg = dedicated_active_config(1)
        if cfg is None:
            print('FAIL: sin PaymentConfig dedicado org 1')
            return 1
        cid = (getattr(cfg, 'paypal_client_id', None) or '').strip()
        mode = (getattr(cfg, 'paypal_mode', None) or '').strip().lower()
        use_env = bool(getattr(cfg, 'use_environment_variables', False))
        ret = (getattr(cfg, 'paypal_return_url', None) or '').strip()
        print(f'PaymentConfig#{cfg.id} use_env={use_env} mode={mode or "(vacío)"}')
        print(f'client_id: {"set" if cid else "MISSING"}')
        print(f'return_url: {ret or "MISSING"}')
        if not cid and not use_env:
            print('→ Checkout seguirá en DEMO hasta guardar credenciales en Admin → Pagos')
            ok = False
        elif mode != 'live':
            print('→ Modo no es live; revisar Admin → Pagos')
            ok = False
        else:
            print('OK: PayPal live configurado (probar pago real en navegador)')
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
