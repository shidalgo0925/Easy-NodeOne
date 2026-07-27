"""Tests admin HTML efactura — NCR/ND desde detalle de emisión."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEfacturaAdminAdjustmentRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    def test_admin_adjustment_routes_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/admin/efactura/emissions/<int:doc_id>/credit-note', rules)
        self.assertIn('/admin/efactura/emissions/<int:doc_id>/debit-note', rules)

    @patch('nodeone.services.efactura_schema.ensure_efactura_schema')
    @patch('nodeone.modules.efactura.config.is_efactura_globally_allowed', return_value=True)
    @patch('nodeone.modules.efactura.admin.routes._guard_module_html', return_value=None)
    @patch('nodeone.modules.efactura.admin.routes._can_admin', return_value=True)
    @patch('nodeone.modules.efactura.admin.routes.is_efactura_enabled_for_org', return_value=True)
    @patch('nodeone.modules.efactura.admin.routes._org_id', return_value=1)
    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.efactura.admin.routes.ElectronicInvoiceDocument')
    @patch('nodeone.modules.efactura.admin.routes.issue_svc.issue_credit_note_from_commercial_invoice')
    def test_emit_credit_note_post(
        self,
        mock_issue,
        mock_doc_cls,
        mock_get_user,
        _oid,
        _enabled,
        _can_admin,
        _guard,
        _global_allowed,
        _schema,
    ):
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = True
        mock_get_user.return_value = user

        parent = MagicMock()
        parent.id = 10
        parent.organization_id = 1
        parent.document_type = 'invoice'
        parent.status = 'accepted'
        parent.invoice_id = 88
        mock_doc_cls.query.filter_by.return_value.first_or_404.return_value = parent

        ncr = MagicMock()
        ncr.id = 11
        ncr.status = 'accepted'
        ncr.cufe = 'CUFE-NCR'
        mock_issue.return_value = ncr

        with self.app.test_request_context():
            from flask import url_for

            action = url_for('efactura_admin.efactura_emit_credit_note', doc_id=10)
        resp = self.client.post(action, data={'reason': 'Devolución'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_issue.assert_called_once_with(88, 1, reason='Devolución')

    @patch('nodeone.services.efactura_schema.ensure_efactura_schema')
    @patch('nodeone.modules.efactura.config.is_efactura_globally_allowed', return_value=True)
    @patch('nodeone.modules.efactura.admin.routes._guard_module_html', return_value=None)
    @patch('nodeone.modules.efactura.admin.routes._can_admin', return_value=True)
    @patch('nodeone.modules.efactura.admin.routes.is_efactura_enabled_for_org', return_value=True)
    @patch('nodeone.modules.efactura.admin.routes._org_id', return_value=1)
    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.efactura.admin.routes.ElectronicInvoiceDocument')
    @patch('nodeone.modules.efactura.admin.routes.issue_svc.issue_debit_note_from_commercial_invoice')
    def test_emit_debit_note_post(
        self,
        mock_issue,
        mock_doc_cls,
        mock_get_user,
        _oid,
        _enabled,
        _can_admin,
        _guard,
        _global_allowed,
        _schema,
    ):
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = True
        mock_get_user.return_value = user

        parent = MagicMock()
        parent.id = 12
        parent.organization_id = 1
        parent.document_type = 'invoice'
        parent.status = 'accepted'
        parent.invoice_id = 90
        mock_doc_cls.query.filter_by.return_value.first_or_404.return_value = parent

        nd = MagicMock()
        nd.id = 13
        nd.status = 'accepted'
        nd.cufe = 'CUFE-ND'
        mock_issue.return_value = nd

        with self.app.test_request_context():
            from flask import url_for

            action = url_for('efactura_admin.efactura_emit_debit_note', doc_id=12)
        resp = self.client.post(action, data={'reason': 'Intereses'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_issue.assert_called_once_with(90, 1, reason='Intereses')


if __name__ == '__main__':
    unittest.main()
