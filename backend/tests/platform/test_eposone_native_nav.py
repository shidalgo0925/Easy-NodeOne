"""Tests navegación nativa EPosOne — UX V3.2."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestNativeAppNavEnabled(unittest.TestCase):
    def test_eposone_seed_org_enables_native_nav(self):
        from nodeone.core.platform.app_nav import native_app_nav_enabled
        from app import app as flask_app

        os.environ['NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS'] = '1'
        os.environ.pop('NODEONE_LAUNCHER_CLASSIC_ORG_IDS', None)
        with flask_app.test_request_context('/admin/eposone/dashboard'):
            self.assertTrue(native_app_nav_enabled(1, 'eposone'))
        with flask_app.test_request_context('/admin/contacts'):
            self.assertFalse(native_app_nav_enabled(1, 'eposone'))
        self.assertFalse(native_app_nav_enabled(1, 'crm'))
        os.environ.pop('NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS', None)

    def test_classic_org_blocks_native_nav(self):
        from nodeone.core.platform.app_nav import native_app_nav_enabled

        os.environ['NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS'] = '1'
        os.environ['NODEONE_LAUNCHER_CLASSIC_ORG_IDS'] = '1'
        self.assertFalse(native_app_nav_enabled(1, 'eposone'))
        os.environ.pop('NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS', None)
        os.environ.pop('NODEONE_LAUNCHER_CLASSIC_ORG_IDS', None)

    def test_contacts_module_not_eposone_zone(self):
        from nodeone.core.platform.app_nav import native_app_nav_enabled, request_in_native_app_zone

        os.environ['NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS'] = '1'
        from app import app as flask_app

        with flask_app.test_request_context('/admin/contacts'):
            self.assertFalse(request_in_native_app_zone('eposone'))
            self.assertFalse(native_app_nav_enabled(1, 'eposone'))
        with flask_app.test_request_context('/admin/eposone/section/orders'):
            self.assertTrue(request_in_native_app_zone('eposone'))
            self.assertTrue(native_app_nav_enabled(1, 'eposone'))
        os.environ.pop('NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS', None)


class TestEposoneNavTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def _ctx(self):
        from nodeone.core.nav_menu import build_nav_context

        return build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda code: code in {'eposone', 'sales', 'analytics'},
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )

    def test_build_tree_domains(self):
        from nodeone.core.platform.app_nav import serialize_nav_sidebar
        from nodeone.modules.eposone.nav import build_nav_tree

        with self.app.test_request_context('/admin/eposone/dashboard'):
            tree = build_nav_tree(self._ctx())
            rows = serialize_nav_sidebar(tree, self._ctx())
        # Sprint UX — operación + Administración + instalación EPosOne
        labels = [r['label'] for r in rows]
        self.assertEqual(
            labels,
            [
                'Dashboard',
                'Pedidos',
                'Productos',
                'Inventario',
                'Clientes',
                'Administración',
                'EPosOne',
                'Más',
            ],
        )
        inventario = next(d for d in tree.domains if d.id == 'inventario')
        self.assertIn('/admin/eposone/section/inventory', inventario.url or '')
        self.assertNotIn('/admin/contador', inventario.url or '')
        self.assertNotIn('Reportes', labels)
        self.assertNotIn('Configuración', labels)
        self.assertNotIn('Infraestructura', labels)
        admin = next(d for d in tree.domains if d.id == 'administracion')
        admin_labels = {c.label for c in admin.children}
        self.assertEqual(
            admin_labels,
            {
                'Empresa',
                'Branding',
                'Sucursales',
                'Puntos de venta',
                'Cajas',
                'Cajeros',
                'Usuarios',
                'Métodos de pago',
                'Impuestos',
                'Licencia',
            },
        )
        epos_ops = next(d for d in tree.domains if d.id == 'eposone-ops')
        epos_labels = {c.label for c in epos_ops.children}
        self.assertEqual(
            epos_labels,
            {'Instalar dispositivo', 'Dispositivos', 'Turnos'},
        )
        # Tenant: sin bloque Plataforma (solo SA)
        self.assertNotIn('Plataforma', labels)
        mas = next(d for d in tree.domains if d.id == 'mas')
        mas_labels = {c.label for c in mas.children}
        self.assertIn('Cocina (KDS)', mas_labels)
        self.assertNotIn('Licencias', mas_labels)
        self.assertNotIn('Centro de configuración', mas_labels)
        self.assertNotIn('Sistema', labels)
        self.assertNotIn('Comercial', labels)

    def test_sa_sees_plataforma_block(self):
        from nodeone.core.nav_menu import build_nav_context
        from nodeone.core.platform.app_nav import serialize_nav_sidebar
        from nodeone.modules.eposone.nav import build_nav_tree

        ctx = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda code: code in {'eposone', 'sales'},
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=True,
            is_platform_admin=True,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        with self.app.test_request_context('/admin/eposone/dashboard'):
            rows = serialize_nav_sidebar(build_nav_tree(ctx), ctx)
        labels = [r['label'] for r in rows]
        self.assertIn('Plataforma', labels)
        plat = next(r for r in rows if r['id'] == 'plataforma-ets')
        child_labels = {c['label'] for c in plat['children']}
        self.assertIn('Organizaciones', child_labels)
        self.assertIn('Módulos SaaS', child_labels)

    def test_clientes_not_contactos(self):
        from nodeone.modules.eposone.nav import build_nav_tree

        with self.app.test_request_context('/admin/eposone/dashboard'):
            tree = build_nav_tree(self._ctx())
        top = {d.label for d in tree.domains}
        self.assertIn('Clientes', top)
        self.assertNotIn('Contactos', top)

    def test_serialize_sidebar_groups(self):
        from nodeone.core.platform.app_nav import serialize_nav_sidebar
        from nodeone.modules.eposone.nav import build_nav_tree

        with self.app.test_request_context('/admin/eposone/dashboard'):
            tree = build_nav_tree(self._ctx())
            rows = serialize_nav_sidebar(tree, self._ctx())
        self.assertTrue(any(r['is_group'] and r['id'] == 'administracion' for r in rows))
        self.assertTrue(any(r['is_group'] and r['id'] == 'eposone-ops' for r in rows))
        self.assertTrue(any(r['is_group'] and r['id'] == 'mas' for r in rows))
        self.assertTrue(any((not r.get('is_group')) and r['id'] == 'pedidos' for r in rows))

class TestMergeNativeAppNav(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    @patch('nodeone.core.platform.app_shell.build_nav_context_for_user')
    @patch('app._org_id_for_module_visibility', return_value=1)
    def test_merge_disables_horizontal_bar(self, _oid, mock_ctx):
        from nodeone.core.nav_menu import build_nav_context
        from nodeone.core.platform.app_shell import merge_native_app_nav_context

        mock_ctx.return_value = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda code: True,
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        os.environ['NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS'] = '1'
        with self.app.test_request_context('/admin/eposone/dashboard'):
            out = {'nav_active_area_id': 'eposone'}
            merge_native_app_nav_context(out, MagicMock(), {})
            self.assertTrue(out.get('app_nav_native_active'))
            self.assertFalse(out.get('nav_show_module_bar'))
            self.assertTrue(out.get('nav_use_context_bar'))
            self.assertEqual(out.get('nav_area_children'), [])
            self.assertTrue(out.get('platform_shell_show_apps_return'))
            self.assertEqual(out.get('platform_apps_return_label'), '← Mis aplicaciones')
            self.assertTrue(out.get('platform_apps_return_url'))
            self.assertEqual(out.get('platform_shell_app_accent'), 'eposone')
            self.assertEqual(out.get('platform_shell_app_product_name'), 'EPosOne')
            self.assertEqual(out.get('platform_shell_app_tagline'), 'Punto de venta')
        os.environ.pop('NODEONE_PLATFORM_SEED_EPOSONE_ORG_IDS', None)

    def test_apps_return_payload_copy(self):
        from nodeone.core.platform.app_shell import _apps_return_payload, _app_identity_payload

        with self.app.test_request_context('/admin/eposone/dashboard'):
            ret = _apps_return_payload()
            ident = _app_identity_payload('eposone')
        self.assertEqual(ret['platform_apps_return_label'], '← Mis aplicaciones')
        self.assertNotIn('Salir', ret['platform_apps_return_label'])
        self.assertEqual(ident['platform_shell_app_accent'], 'eposone')
        self.assertEqual(ident['platform_shell_app_product_name'], 'EPosOne')


class TestMergeAppShellContacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    @patch('nodeone.core.platform.app_shell.launcher_mode_for_organization', return_value='apps')
    @patch('nodeone.core.platform.app_shell.get_active_app_id', return_value='eposone')
    @patch('nodeone.core.platform.app_shell.build_nav_context_for_user')
    @patch('app._org_id_for_module_visibility', return_value=1)
    def test_contacts_page_not_eposone_shell(self, _oid, mock_ctx, _active, _mode):
        from nodeone.core.nav_menu import build_nav_context, nav_launcher_payload
        from nodeone.core.platform.app_shell import merge_app_shell_nav_context

        mock_ctx.return_value = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda code: code in {'contacts', 'eposone', 'sales'},
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        session = {'platform_active_app_id': 'eposone'}
        with self.app.test_request_context('/admin/contacts'):
            out = nav_launcher_payload(
                nav_can=lambda _p: True,
                saas_module_enabled=lambda code: code in {'contacts', 'eposone', 'sales'},
                saas_module_enabled_chain=lambda *_c: True,
                has_view_endpoint=lambda _e: True,
                show_academic_admin_nav=False,
                office365_module_enabled=False,
                show_platform_admin_nav=False,
                is_platform_admin=False,
                is_advisor=False,
                show_tenant_admin_menu=True,
            )
            merge_app_shell_nav_context(out, MagicMock(), session)
            self.assertEqual(out.get('nav_active_area_id'), 'contactos')
            self.assertFalse(out.get('platform_app_shell_active'))
            self.assertFalse(out.get('nav_show_module_bar'))
            self.assertNotEqual(out.get('platform_shell_app_label'), 'EPosOne')


class TestEposoneSidebarEntry(unittest.TestCase):
    def test_eposone_in_sidebar_top_level(self):
        from nodeone.core.nav_menu import build_nav_context, visible_sidebar_launcher

        ctx = build_nav_context(
            nav_can=lambda _p: True,
            saas_module_enabled=lambda code: code == 'eposone',
            saas_module_enabled_chain=lambda *_c: True,
            has_view_endpoint=lambda _e: True,
            show_academic_admin_nav=False,
            office365_module_enabled=False,
            show_platform_admin_nav=False,
            is_platform_admin=False,
            is_advisor=False,
            show_tenant_admin_menu=True,
        )
        top, _groups = visible_sidebar_launcher(ctx)
        self.assertIn('eposone', [a['id'] for a in top])
        epos = next(a for a in top if a['id'] == 'eposone')
        self.assertTrue(epos.get('temporary_app_shortcut'))
        self.assertEqual(epos.get('badge'), 'App')
        self.assertIn('temporal', (epos.get('title') or '').lower())
        contactos = next((a for a in top if a['id'] == 'contactos'), None)
        if contactos:
            self.assertFalse(contactos.get('temporary_app_shortcut'))


if __name__ == '__main__':
    unittest.main()
