"""Tests admin: listado y eliminación de certificados emitidos (membresía)."""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import certificate_routes as routes


class TestCertificateAdminIssued(unittest.TestCase):
    def test_user_display_name_from_parts(self):
        user = SimpleNamespace(id=5, first_name='Ana', last_name='López', email='a@x.com')
        self.assertEqual(routes._user_display_name(user), 'Ana López')

    def test_user_display_name_fallback_email(self):
        user = SimpleNamespace(id=5, first_name='', last_name='', email='solo@x.com')
        self.assertEqual(routes._user_display_name(user), 'solo@x.com')

    def test_remove_certificate_pdf_file_only_inside_allowed_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            allowed = os.path.join(tmp, 'certs') + os.sep
            os.makedirs(allowed, exist_ok=True)
            pdf = os.path.join(allowed, 'PLAN-2026-0001.pdf')
            with open(pdf, 'wb') as f:
                f.write(b'%PDF')
            outside = os.path.join(tmp, 'other.pdf')
            with open(outside, 'wb') as f:
                f.write(b'%PDF')

            with patch.object(routes, '_certificates_pdf_dir', return_value=allowed):
                routes._remove_certificate_pdf_file(pdf)
                routes._remove_certificate_pdf_file(outside)

            self.assertFalse(os.path.isfile(pdf))
            self.assertTrue(os.path.isfile(outside))

    def test_certificate_to_admin_dict(self):
        user = SimpleNamespace(id=1, first_name='Bo', last_name='Li', email='b@x.com')
        cert = SimpleNamespace(
            id=10,
            certificate_code='PLAN-BASIC-2026-0001',
            user_id=1,
            user=user,
            generated_at=None,
            status='generated',
        )
        d = routes._certificate_to_admin_dict(cert)
        self.assertEqual(d['certificate_code'], 'PLAN-BASIC-2026-0001')
        self.assertEqual(d['user_name'], 'Bo Li')
        self.assertEqual(d['user_email'], 'b@x.com')


if __name__ == '__main__':
    unittest.main()
