"""Tests ADR-012 — Product Registry + ContextResolver (Host → producto → apps)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestProductRegistry(unittest.TestCase):
    def setUp(self):
        from nodeone.core.platform.context_resolver import reload_config

        reload_config()

    def test_get_eposone(self):
        from nodeone.core.platform.product_registry import ProductRegistry

        p = ProductRegistry.get('eposone')
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p.name, 'EPosOne')
        self.assertEqual(p.primary_domain, 'eposone.easytech.services')
        self.assertEqual(p.surface, 'product')
        self.assertEqual(p.app_ids, ('eposone',))
        self.assertTrue(p.list_in_portal)
        self.assertEqual(p.licensing.get('saas_code'), 'eposone')

    def test_list_for_portal_excludes_platform_and_legacy(self):
        from nodeone.core.platform.product_registry import ProductRegistry

        codes = {p.code for p in ProductRegistry.list_for_portal()}
        self.assertIn('eposone', codes)
        self.assertIn('epayroll', codes)
        self.assertNotIn('en1', codes)
        self.assertNotIn('portal', codes)
        self.assertNotIn('iius', codes)
        self.assertNotIn('relatic', codes)

    def test_resolve_apps_uses_app_registry(self):
        from nodeone.core.platform.product_registry import ProductRegistry

        p = ProductRegistry.get_or_default('eposone')
        apps = p.resolve_apps()
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, 'eposone')
        self.assertEqual(apps[0].saas_codes, ('eposone',))

    def test_unknown_falls_back_to_en1(self):
        from nodeone.core.platform.product_registry import ProductRegistry

        d = ProductRegistry.get_or_default('no-existe')
        self.assertEqual(d.code, 'en1')


class TestContextResolverHost(unittest.TestCase):
    def setUp(self):
        from nodeone.core.platform.context_resolver import reload_config

        reload_config()

    def test_exact_hosts_product_and_brand(self):
        from nodeone.core.platform.context_resolver import ContextResolver

        en1 = ContextResolver.resolve('appdev.easynodeone.com')
        self.assertEqual(en1.product.code, 'en1')
        self.assertEqual(en1.product.surface, 'platform')
        self.assertEqual(en1.brand.display_name, 'Easy NodeOne')

        prd = ContextResolver.resolve('appprd.easynodeone.com')
        self.assertEqual(prd.product_code, 'en1')
        self.assertEqual(prd.surface, 'platform')

        epo = ContextResolver.resolve('eposone.easytech.services')
        self.assertEqual(epo.product.code, 'eposone')
        self.assertEqual(epo.product.surface, 'product')
        self.assertEqual(epo.brand.display_name, 'EPosOne')
        self.assertEqual(epo.brand.theme_primary, '#FF6600')
        self.assertEqual(epo.product.allowed_apps, ('eposone',))
        self.assertEqual(epo.brand.logo_url, 'images/logo-eposone-brand.jpg')
        self.assertEqual(epo.product.home_hint, 'eposone.eposone_home')
        self.assertEqual(epo.brand.brand_preset, 'eposone')

        platform = ContextResolver.resolve('appprd.easynodeone.com')
        self.assertEqual(platform.product.code, 'en1')
        self.assertEqual(platform.product.surface, 'platform')
        self.assertEqual(platform.brand.display_name, 'Easy NodeOne')

    def test_prefix_and_aliases(self):
        from nodeone.core.platform.context_resolver import ContextResolver

        self.assertEqual(
            ContextResolver.resolve_product_code('eposone-stg.easytech.services'),
            'eposone',
        )
        self.assertEqual(
            ContextResolver.resolve_product_code('epayroll.easytech.services'),
            'epayroll',
        )
        self.assertEqual(
            ContextResolver.resolve_product_code('tonydev.easynodeone.com'),
            'en1',
        )

    def test_separate_accessors(self):
        from nodeone.core.platform.context_resolver import (
            ContextResolver,
            resolve_brand_context,
            resolve_product_context,
        )

        product = resolve_product_context('eposone.easytech.services')
        brand = resolve_brand_context('eposone.easytech.services')
        self.assertEqual(product.code, 'eposone')
        self.assertEqual(brand.display_name, 'EPosOne')
        self.assertEqual(ContextResolver.resolve_product('eposone.easytech.services').code, product.code)

    def test_compat_brand_context_module(self):
        from nodeone.core.platform.brand_context import (
            resolve_brand_context,
            resolve_product_code,
        )

        self.assertEqual(resolve_product_code('appdev.easynodeone.com'), 'en1')
        self.assertEqual(resolve_brand_context('eposone.easytech.services').display_name, 'EPosOne')

    def test_template_dict_keys(self):
        from nodeone.core.platform.context_resolver import ContextResolver

        d = ContextResolver.resolve('eposone.easytech.services').to_template_dict()
        self.assertEqual(d['product_code'], 'eposone')
        self.assertEqual(d['product_surface'], 'product')
        self.assertEqual(d['product_display_name'], 'EPosOne')
        self.assertIn('brand_preset', d)

    def test_three_layer_questions(self):
        """Host → código; ProductRegistry → definición; AppRegistry → apps."""
        from nodeone.core.platform.context_resolver import ContextResolver
        from nodeone.core.platform.product_registry import ProductRegistry

        code = ContextResolver.resolve_product_code('eposone.easytech.services')
        self.assertEqual(code, 'eposone')
        definition = ProductRegistry.get(code)
        self.assertIsNotNone(definition)
        assert definition is not None
        self.assertEqual(definition.name, 'EPosOne')
        self.assertEqual([a.id for a in definition.resolve_apps()], ['eposone'])


if __name__ == '__main__':
    unittest.main()
