"""Turnstile helpers — sin keys no exige verificación."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestTurnstileConfig(unittest.TestCase):
    def test_disabled_without_keys(self):
        from nodeone.services.cloudflare_turnstile import (
            require_turnstile_from_request,
            turnstile_enabled,
            turnstile_template_vars,
        )

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('CLOUDFLARE_TURNSTILE_SITE_KEY', None)
            os.environ.pop('CLOUDFLARE_TURNSTILE_SECRET_KEY', None)
            os.environ.pop('CLOUDFLARE_TURNSTILE_ENABLED', None)
            self.assertFalse(turnstile_enabled())
            vars_ = turnstile_template_vars()
            self.assertFalse(vars_['turnstile_enabled'])
            self.assertEqual(vars_['turnstile_site_key'], '')

            class _Req:
                form = {}
                headers = {}
                remote_addr = '127.0.0.1'

            ok, err = require_turnstile_from_request(_Req())
            self.assertTrue(ok)
            self.assertEqual(err, '')

    def test_enabled_with_keys(self):
        from nodeone.services.cloudflare_turnstile import turnstile_enabled

        env = {
            'CLOUDFLARE_TURNSTILE_SITE_KEY': 'site',
            'CLOUDFLARE_TURNSTILE_SECRET_KEY': 'secret',
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertTrue(turnstile_enabled())


if __name__ == '__main__':
    unittest.main()
