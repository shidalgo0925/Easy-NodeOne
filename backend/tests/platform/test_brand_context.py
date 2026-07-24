"""Tests ADR-011 — ContextResolver / BrandContext / ProductContext por Host."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


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
        self.assertEqual(epo.brand.theme_primary, '#FF6B35')

        portal = ContextResolver.resolve('portal.easytech.services')
        self.assertEqual(portal.product.surface, 'portal')
        self.assertEqual(portal.brand.display_name, 'EasyTech Services')

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
        self.assertIs(ContextResolver.resolve_product('eposone.easytech.services').code, product.code)

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


if __name__ == '__main__':
    unittest.main()
