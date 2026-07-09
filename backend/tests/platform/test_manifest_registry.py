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
        from nodeone.core.platform.manifest_registry import validate_manifest

        m = {
            'id': 'ehr',
            'name': 'EHR',
            'saas_codes': ('ehr',),
            'lifecycle': 'planned',
        }
        self.assertEqual(validate_manifest(m), [])

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

    def test_platform_apps_health(self):
        from nodeone.core.platform.manifest_registry import platform_apps_health

        health = platform_apps_health()
        self.assertTrue(health['alignment_ok'])
        self.assertTrue(health['registry_ok'])
        self.assertTrue(health['saas_catalog_ok'])
        self.assertEqual(health['errors'], [])
        self.assertGreaterEqual(health['manifest_count'], 5)
        self.assertIn('eposone', health['app_ids'])

    def test_manifest_summary(self):
        from nodeone.core.platform.manifest_registry import load_manifest, manifest_summary

        m = load_manifest('nodeone.modules.eposone.manifest')
        summary = manifest_summary(m)
        self.assertEqual(summary['id'], 'eposone')
        self.assertTrue(summary['has_register'])
        self.assertIn('eposone', summary['saas_codes'])

    def test_saas_catalog_alignment(self):
        from nodeone.core.platform.manifest_registry import saas_catalog_alignment_errors

        self.assertEqual(saas_catalog_alignment_errors(), [])

    def test_eposone_checklist_ready(self):
        from nodeone.core.platform.manifest_registry import platform_app_checklist

        result = platform_app_checklist('eposone')
        self.assertTrue(result['found'])
        self.assertTrue(result['ready'])
        self.assertTrue(result['checklist']['saas_catalog_codes'])
        self.assertTrue(result['checklist']['launcher_nav_mapping'])

    def test_checklist_unknown_app(self):
        from nodeone.core.platform.manifest_registry import platform_app_checklist

        result = platform_app_checklist('no_such_app')
        self.assertFalse(result['found'])
        self.assertFalse(result['ready'])


class TestPlatformAppScaffold(unittest.TestCase):
    def test_normalize_app_id(self):
        from nodeone.core.platform.app_scaffold import normalize_app_id

        self.assertEqual(normalize_app_id('My-App'), 'my_app')
        with self.assertRaises(ValueError):
            normalize_app_id('1bad')

    def test_scaffold_file_map(self):
        from nodeone.core.platform.app_scaffold import build_scaffold_spec, scaffold_file_map

        spec = build_scaffold_spec(app_id='demoapp', name='Demo App')
        root = Path(__file__).resolve().parent.parent.parent.parent
        files = scaffold_file_map(spec, app_root=root)
        self.assertIn(root / 'backend' / 'nodeone' / 'modules' / 'demoapp' / 'manifest.py', files)
        self.assertIn("id': 'demoapp'", files[root / 'backend' / 'nodeone' / 'modules' / 'demoapp' / 'manifest.py'])

    def test_dry_run_no_write(self):
        from nodeone.core.platform.app_scaffold import build_scaffold_spec, write_scaffold

        spec = build_scaffold_spec(app_id='tmpapp', name='Tmp')
        result = write_scaffold(spec, app_root=Path('/tmp/en1_scaffold_test'), dry_run=True)
        self.assertTrue(result['dry_run'])
        self.assertEqual(len(result['files']), 6)


class TestPlatformAppsAPI(unittest.TestCase):
    def test_manifests_route_registered(self):
        from app import app as flask_app

        rules = {r.rule for r in flask_app.url_map.iter_rules()}
        self.assertIn('/api/platform/apps/manifests', rules)
        self.assertIn('/api/platform/apps/manifests/<app_id>/checklist', rules)
        self.assertIn('/api/platform/apps/health', rules)
        self.assertIn('/api/platform/apps/template', rules)
        self.assertIn('/api/platform/master/org-units', rules)
        self.assertIn('/api/platform/master/org-units/<unit_ref>', rules)
        self.assertIn('/api/platform/master/me/linked-contact', rules)
        self.assertIn('/api/platform/master/contacts/resolve/<int:contact_id>', rules)
        self.assertIn('/api/platform/master/contacts/legacy-links', rules)


class TestPlatformMasterAPI(unittest.TestCase):
    def test_branches_api_route_registered(self):
        from app import app as flask_app

        rules = {r.rule for r in flask_app.url_map.iter_rules()}
        self.assertIn('/api/eposone/branches', rules)
        self.assertIn('/api/eposone/branches/<unit_ref>', rules)
        self.assertIn('/api/eposone/products', rules)
        self.assertIn('/api/eposone/products/<product_ref>', rules)
        self.assertIn('/api/eposone/stock-balances', rules)
        self.assertIn('/api/eposone/warehouses', rules)
        self.assertIn('/api/eposone/registers', rules)
        self.assertIn('/api/eposone/pos-units', rules)
        self.assertIn('/api/eposone/orders/<int:order_id>/fiscal', rules)
        self.assertIn('/api/eposone/orders/<int:order_id>/split', rules)


if __name__ == '__main__':
    unittest.main()
