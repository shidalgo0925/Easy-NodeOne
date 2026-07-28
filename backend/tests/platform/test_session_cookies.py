"""Cookie Domain: host-only por defecto."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from nodeone.core.platform.session_cookies import cookie_domain_for_host


class TestCookieDomainForHost(unittest.TestCase):
    def test_host_only_by_default(self):
        self.assertIsNone(cookie_domain_for_host('eposone.easytech.services'))
        self.assertIsNone(cookie_domain_for_host('epayroll.easytech.services'))
        self.assertIsNone(cookie_domain_for_host('easytech.services'))
        self.assertIsNone(cookie_domain_for_host('appprd.easynodeone.com'))
        self.assertIsNone(cookie_domain_for_host('appdev.easynodeone.com'))
        self.assertIsNone(cookie_domain_for_host('localhost'))

    def test_env_opt_in(self):
        with patch.dict(os.environ, {'NODEONE_SESSION_COOKIE_DOMAIN': '.easytech.services'}):
            self.assertEqual(cookie_domain_for_host('eposone.easytech.services'), '.easytech.services')
            self.assertEqual(cookie_domain_for_host('appprd.easynodeone.com'), '.easytech.services')


if __name__ == '__main__':
    unittest.main()
