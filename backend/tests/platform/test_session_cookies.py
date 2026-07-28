"""Cookie Domain ETS vs EN1."""
from __future__ import annotations

import unittest

from nodeone.core.platform.session_cookies import cookie_domain_for_host


class TestCookieDomainForHost(unittest.TestCase):
    def test_ets_product_and_portal(self):
        self.assertEqual(cookie_domain_for_host('eposone.easytech.services'), '.easytech.services')
        self.assertEqual(cookie_domain_for_host('app.easytech.services'), '.easytech.services')
        self.assertEqual(cookie_domain_for_host('portal.easytech.services'), '.easytech.services')
        self.assertEqual(cookie_domain_for_host('easytech.services'), '.easytech.services')

    def test_en1_host_only(self):
        self.assertIsNone(cookie_domain_for_host('appprd.easynodeone.com'))
        self.assertIsNone(cookie_domain_for_host('appdev.easynodeone.com'))
        self.assertIsNone(cookie_domain_for_host('localhost'))


if __name__ == '__main__':
    unittest.main()
