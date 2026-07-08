"""Tests Launcher v2 (Etapa 3)."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestLauncherMode(unittest.TestCase):
    def tearDown(self):
        for key in (
            'NODEONE_LAUNCHER_MODE',
            'NODEONE_LAUNCHER_APPS_ORG_IDS',
            'NODEONE_LAUNCHER_CLASSIC_ORG_IDS',
        ):
            os.environ.pop(key, None)

    def test_default_classic(self):
        from nodeone.core.platform.launcher import launcher_mode_for_organization

        self.assertEqual(launcher_mode_for_organization(1), 'classic')

    def test_apps_org_override(self):
        from nodeone.core.platform.launcher import launcher_mode_for_organization

        os.environ['NODEONE_LAUNCHER_APPS_ORG_IDS'] = '1'
        self.assertEqual(launcher_mode_for_organization(1), 'apps')
        self.assertEqual(launcher_mode_for_organization(2), 'classic')

    def test_classic_org_override_wins(self):
        from nodeone.core.platform.launcher import launcher_mode_for_organization

        os.environ['NODEONE_LAUNCHER_MODE'] = 'apps'
        os.environ['NODEONE_LAUNCHER_CLASSIC_ORG_IDS'] = '2'
        self.assertEqual(launcher_mode_for_organization(1), 'apps')
        self.assertEqual(launcher_mode_for_organization(2), 'classic')


class TestLauncherRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_apps_home_classic_redirects_admin(self):
        with patch('nodeone.core.platform.launcher.launcher_mode_for_organization', return_value='classic'):
            with self.app.test_client() as c:
                # sin login → login redirect
                r = c.get('/platform/apps', follow_redirects=False)
                self.assertIn(r.status_code, (302, 401))

    def test_platform_launcher_blueprint_registered(self):
        self.assertIn('platform_launcher', self.app.blueprints)


class TestPostLoginRedirect(unittest.TestCase):
    def test_member_goes_dashboard(self):
        from nodeone.core.platform.launcher import post_login_redirect_target

        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = False
        session = {}
        with patch('nodeone.core.template_context_gates.user_can_see_tenant_admin_menu', return_value=False):
            with patch('flask.url_for', return_value='/dashboard'):
                dest = post_login_redirect_target(next_page=None, user=user, session=session)
        self.assertEqual(dest, '/dashboard')

    def test_respects_explicit_next(self):
        from nodeone.core.platform.launcher import post_login_redirect_target

        user = MagicMock()
        session = {}
        dest = post_login_redirect_target(next_page='/custom', user=user, session=session)
        self.assertEqual(dest, '/custom')


if __name__ == '__main__':
    unittest.main()
