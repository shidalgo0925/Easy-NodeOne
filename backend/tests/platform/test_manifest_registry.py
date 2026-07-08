"""Tests manifest registry — Etapa 9."""

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestManifestRegistry(unittest.TestCase):
    def test_discover_includes_integrated_and_planned_apps(self):
        from nodeone.core.platform.manifest_registry import discover_platform_manifests

        manifests = discover_platform_manifests()
        self.assertIn('emembership', manifests)
        self.assertIn('eposone', manifests)
        self.assertIn('epayroll', manifests)

    def test_validate_emembership_manifest(self):
        from nodeone.core.platform.manifest_registry import load_manifest, validate_manifest

        m = load_manifest('nodeone.modules.emembership.manifest')
        self.assertEqual(validate_manifest(m), [])

    def test_validate_planned_without_register(self):
        from nodeone.core.platform.manifest_registry import load_manifest, validate_manifest

        m = load_manifest('nodeone.modules.epayroll.manifest')
        self.assertEqual(validate_manifest(m), [])
        self.assertEqual(m.get('lifecycle'), 'planned')
        self.assertNotIn('register', m)

    def test_active_manifest_requires_register(self):
        from nodeone.core.platform.manifest_registry import validate_manifest

        errors = validate_manifest({'id': 'x', 'name': 'X', 'saas_codes': ('x',)})
        self.assertTrue(any('register' in e for e in errors))

    def test_registry_alignment(self):
        from nodeone.core.platform.manifest_registry import registry_alignment_errors

        errors = registry_alignment_errors()
        self.assertEqual(errors, [])

    def test_new_app_template_has_required_keys(self):
        from nodeone.core.platform.manifest_registry import (
            NEW_APP_MANIFEST_TEMPLATE,
            REQUIRED_MANIFEST_KEYS,
            validate_manifest,
        )

        self.assertTrue(REQUIRED_MANIFEST_KEYS <= set(NEW_APP_MANIFEST_TEMPLATE.keys()))
        # planned template may omit register until activation
        tpl = dict(NEW_APP_MANIFEST_TEMPLATE)
        tpl['lifecycle'] = 'planned'
        tpl.pop('register', None)
        self.assertEqual(validate_manifest(tpl), [])


if __name__ == '__main__':
    unittest.main()
