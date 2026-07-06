"""Rutas PDF certificados de membresía (regresión post-refactor api_routes)."""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from nodeone.services import certificate_http as ch


class TestMembershipCertificatePdfPaths(unittest.TestCase):
    def test_membership_dir_under_repo_instance(self):
        app = SimpleNamespace(root_path='/opt/easynodeone/dev/app/backend')
        d = ch.membership_certificates_pdf_dir(app=app)
        self.assertTrue(d.endswith(f'{os.sep}instance{os.sep}certificates{os.sep}'))
        self.assertIn('/dev/app/instance/certificates', d.replace('\\', '/'))

    def test_resolve_legacy_silo_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            legacy_root = os.path.join(tmp, 'relatic', 'app', 'instance', 'certificates')
            os.makedirs(legacy_root, exist_ok=True)
            pdf = os.path.join(legacy_root, 'PLAN-PRO-O1-2026-0001.pdf')
            with open(pdf, 'wb') as f:
                f.write(b'%PDF')
            app = SimpleNamespace(root_path=os.path.join(tmp, 'dev', 'app', 'backend'))
            resolved = ch.resolve_membership_certificate_pdf_path(
                pdf,
                'PLAN-PRO-O1-2026-0001',
                app=app,
            )
            self.assertEqual(resolved, os.path.normpath(os.path.realpath(pdf)))

    def test_resolve_by_code_in_canonical_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = SimpleNamespace(root_path=os.path.join(tmp, 'app', 'backend'))
            canon = ch.membership_certificates_pdf_dir(app=app).rstrip(os.sep)
            pdf = os.path.join(canon, 'MEM-O1-2026-0009.pdf')
            with open(pdf, 'wb') as f:
                f.write(b'%PDF')
            resolved = ch.resolve_membership_certificate_pdf_path(
                '/wrong/path/MEM-O1-2026-0009.pdf',
                'MEM-O1-2026-0009',
                app=app,
            )
            self.assertEqual(resolved, os.path.normpath(os.path.realpath(pdf)))


if __name__ == '__main__':
    unittest.main()
