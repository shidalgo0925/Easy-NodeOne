"""ADR-017 Hito 1 — Portal Público del Producto."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestProductLandingContent(unittest.TestCase):
    def test_eposone_has_full_sections(self):
        from nodeone.modules.product_landing.content import landing_content_for

        c = landing_content_for(
            'eposone',
            display_name='EPosOne',
            tagline='Punto de venta',
            description='POS',
        )
        self.assertEqual(c['template'], 'product_landing/eposone.html')
        self.assertEqual(c['demo']['source'], 'eposone-landing')
        self.assertGreaterEqual(len(c['pillars']), 4)
        self.assertEqual(len(c['plans']), 3)
        self.assertEqual(c['plans'][0]['name'], 'Starter')
        self.assertIn('29.95', c['plans'][0]['price'])
        self.assertEqual(c['plans'][1]['name'], 'Business')
        self.assertIn('39.95', c['plans'][1]['price'])
        self.assertEqual(c['plans'][2]['name'], 'Enterprise')
        self.assertIn('79.95', c['plans'][2]['price'])
        self.assertEqual(len(c['services_included']['entries']), 6)
        self.assertEqual(len(c['services_optional']['entries']), 7)
        self.assertFalse(c['modules']['entries'][2]['included'])  # CRM
        self.assertFalse(c['modules']['entries'][3]['included'])  # Marketing
        self.assertTrue(c['modules']['entries'][0]['included'])  # POS
        self.assertGreaterEqual(len(c['faq']), 3)
        self.assertIn('Vende más', c['hero']['tagline'])
        self.assertEqual(c['hero']['side_image'], 'images/eposone-landing-hero-side.png')
        self.assertEqual(len(c['modules']['entries']), 6)

    def test_generic_fallback(self):
        from nodeone.modules.product_landing.content import landing_content_for

        c = landing_content_for(
            'epayroll',
            display_name='EPayRoll',
            tagline='Nómina',
            description='Nómina y empleados',
        )
        self.assertEqual(c['template'], 'product_landing/generic.html')
        self.assertEqual(c['demo']['source'], 'epayroll-landing')
        self.assertTrue(c['benefits'])

    def test_index_serves_landing_on_product_host(self):
        from nodeone.core.platform.context_resolver import ContextResolver

        ctx = ContextResolver.resolve('eposone.easytech.services')
        self.assertEqual(ctx.surface, 'product')
        self.assertEqual(ctx.product_code, 'eposone')


if __name__ == '__main__':
    unittest.main()
