"""Tests emisión NCR/ND efactura — Fase D."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCreditNoteMapper(unittest.TestCase):
    @patch('nodeone.modules.efactura.services.mapper.build_invoice_payload')
    def test_build_credit_note_payload_references_parent_cufe(self, mock_invoice_payload):
        from nodeone.modules.efactura.services.mapper import build_credit_note_payload

        mock_invoice_payload.return_value = {
            'datosGenerales': {'tipoDocumento': '01', 'informacionInteresEmisor': 'Factura'},
            'listaItems': [],
            'totales': {},
        }
        payload = build_credit_note_payload(
            SimpleNamespace(default_pos='001'),
            SimpleNamespace(id=5, number='INV-5'),
            [],
            SimpleNamespace(),
            parent_cufe='CUFE-PARENT-123',
            reason='Devolución total',
        )
        self.assertEqual(payload['datosGenerales']['tipoDocumento'], '04')
        refs = payload['datosGenerales']['documentosFiscalesReferenciados']
        self.assertEqual(refs[0]['cufeFEReferenciado'], 'CUFE-PARENT-123')


class TestDebitNoteMapper(unittest.TestCase):
    @patch('nodeone.modules.efactura.services.mapper.build_invoice_payload')
    def test_build_debit_note_payload_references_parent_cufe(self, mock_invoice_payload):
        from nodeone.modules.efactura.services.mapper import build_debit_note_payload

        mock_invoice_payload.return_value = {
            'datosGenerales': {'tipoDocumento': '01', 'informacionInteresEmisor': 'Factura'},
            'listaItems': [],
            'totales': {},
        }
        payload = build_debit_note_payload(
            SimpleNamespace(default_pos='001'),
            SimpleNamespace(id=5, number='INV-5'),
            [],
            SimpleNamespace(),
            parent_cufe='CUFE-PARENT-456',
            reason='Intereses',
        )
        self.assertEqual(payload['datosGenerales']['tipoDocumento'], '05')
        refs = payload['datosGenerales']['documentosFiscalesReferenciados']
        self.assertEqual(refs[0]['cufeFEReferenciado'], 'CUFE-PARENT-456')
        self.assertIn('motivoNotaDebito', refs[0])


class TestCommerceFiscalForceEmit(unittest.TestCase):
    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService._try_issue_fe', return_value=True)
    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService._ensure_accounting_invoice', return_value=12)
    @patch('nodeone.core.commerce.fiscal.CoreCommercialOrder')
    def test_process_pending_order_passes_force_emit(self, mock_order_cls, _ensure, mock_try):
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        order = MagicMock()
        order.fiscal_status = 'pending'
        order.contact_id = 3
        order.order_ref = 'POS-1'
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = CommerceFiscalService.process_pending_order(1, 9, force_emit=True)
        self.assertEqual(result['status'], 'issued')
        mock_try.assert_called_once()
        self.assertTrue(mock_try.call_args.kwargs.get('force_emit'))


class TestIssueCreditNoteService(unittest.TestCase):
    @patch('nodeone.modules.efactura.services.issue.db')
    @patch('nodeone.modules.efactura.services.issue._adapter_for')
    @patch('nodeone.modules.efactura.services.issue._log_event')
    @patch('nodeone.modules.efactura.services.mapper.build_credit_note_payload', return_value={'datosGenerales': {}})
    @patch('nodeone.modules.efactura.services.issue.cfg_svc')
    @patch('nodeone.modules.efactura.services.issue.is_efactura_enabled_for_org', return_value=True)
    @patch('nodeone.modules.efactura.services.issue.find_accepted_fe_for_invoice')
    @patch('nodeone.modules.efactura.services.issue.InvoiceLine')
    @patch('nodeone.modules.efactura.services.issue.get_invoice_fiscal_contact')
    @patch('nodeone.modules.efactura.services.issue.Invoice')
    @patch('nodeone.modules.efactura.services.issue.ElectronicInvoiceDocument')
    def test_issue_credit_note_from_commercial_invoice(
        self,
        mock_doc_cls,
        mock_invoice_cls,
        mock_get_contact,
        mock_line_cls,
        mock_find_parent,
        _enabled,
        mock_cfg,
        _mapper,
        _log,
        mock_adapter_for,
        mock_db,
    ):
        from nodeone.modules.efactura.services.issue import issue_credit_note_from_commercial_invoice

        inv = MagicMock()
        inv.id = 8
        inv.number = 'POS-0008'
        inv.contact_id = 2
        inv.total = 20.0
        inv.tax_total = 0.0
        inv.grand_total = 20.0
        inv.currency = 'USD'
        inv.status = 'paid'
        mock_invoice_cls.query.filter_by.return_value.first.return_value = inv

        parent = MagicMock()
        parent.id = 50
        parent.cufe = 'CUFE-ABC'
        parent.status = 'accepted'
        mock_find_parent.return_value = parent
        mock_doc_cls.query.filter.return_value.order_by.return_value.first.return_value = None

        contact = MagicMock()
        contact.id = 2
        contact.tax_id = '8-123'
        mock_get_contact.return_value = contact
        mock_line_cls.query.filter_by.return_value.order_by.return_value.all.return_value = []

        config = MagicMock()
        config.provider = 'efacturapty'
        config.environment = 'sandbox'
        config.default_currency = 'USD'
        mock_cfg.get_or_create_provider_config.return_value = config
        mock_cfg.config_ready.return_value = True

        adapter = MagicMock()
        adapter.emit_credit_note.return_value = {
            'autorizada': True,
            'cufe': 'CUFE-NCR',
            'protocolo': 'P1',
            'authorization_message': 'OK',
            'raw_response': {},
            'http_status': 200,
        }
        mock_adapter_for.return_value = adapter

        with patch('nodeone.modules.efactura.services.issue.contact_fiscal_email', return_value='a@b.com'):
            with patch('nodeone.modules.efactura.services.issue.fiscal_display_name', return_value='Cliente'):
                doc = issue_credit_note_from_commercial_invoice(8, 1, reason='Devolución total')

        self.assertEqual(doc.status, 'accepted')
        adapter.emit_credit_note.assert_called_once()
        self.assertEqual(parent.status, 'credited')


class TestIssueDebitNoteService(unittest.TestCase):
    @patch('nodeone.modules.efactura.services.issue.db')
    @patch('nodeone.modules.efactura.services.issue._adapter_for')
    @patch('nodeone.modules.efactura.services.issue._log_event')
    @patch('nodeone.modules.efactura.services.mapper.build_debit_note_payload', return_value={'datosGenerales': {}})
    @patch('nodeone.modules.efactura.services.issue.cfg_svc')
    @patch('nodeone.modules.efactura.services.issue.is_efactura_enabled_for_org', return_value=True)
    @patch('nodeone.modules.efactura.services.issue.find_accepted_fe_for_invoice')
    @patch('nodeone.modules.efactura.services.issue.InvoiceLine')
    @patch('nodeone.modules.efactura.services.issue.get_invoice_fiscal_contact')
    @patch('nodeone.modules.efactura.services.issue.Invoice')
    @patch('nodeone.modules.efactura.services.issue.ElectronicInvoiceDocument')
    def test_issue_debit_note_from_commercial_invoice(
        self,
        mock_doc_cls,
        mock_invoice_cls,
        mock_get_contact,
        mock_line_cls,
        mock_find_parent,
        _enabled,
        mock_cfg,
        _mapper,
        _log,
        mock_adapter_for,
        mock_db,
    ):
        from nodeone.modules.efactura.services.issue import issue_debit_note_from_commercial_invoice

        inv = MagicMock()
        inv.id = 9
        inv.number = 'POS-0009'
        inv.contact_id = 2
        inv.total = 15.0
        inv.tax_total = 0.0
        inv.grand_total = 15.0
        inv.currency = 'USD'
        inv.status = 'paid'
        mock_invoice_cls.query.filter_by.return_value.first.return_value = inv

        parent = MagicMock()
        parent.id = 51
        parent.cufe = 'CUFE-XYZ'
        parent.status = 'accepted'
        mock_find_parent.return_value = parent
        mock_doc_cls.query.filter.return_value.order_by.return_value.first.return_value = None

        contact = MagicMock()
        contact.id = 2
        mock_get_contact.return_value = contact
        mock_line_cls.query.filter_by.return_value.order_by.return_value.all.return_value = []

        config = MagicMock()
        config.provider = 'efacturapty'
        config.environment = 'sandbox'
        config.default_currency = 'USD'
        mock_cfg.get_or_create_provider_config.return_value = config
        mock_cfg.config_ready.return_value = True

        adapter = MagicMock()
        adapter.emit_debit_note.return_value = {
            'autorizada': True,
            'cufe': 'CUFE-ND',
            'protocolo': 'P2',
            'authorization_message': 'OK',
            'raw_response': {},
            'http_status': 200,
        }
        mock_adapter_for.return_value = adapter

        with patch('nodeone.modules.efactura.services.issue.contact_fiscal_email', return_value='a@b.com'):
            with patch('nodeone.modules.efactura.services.issue.fiscal_display_name', return_value='Cliente'):
                doc = issue_debit_note_from_commercial_invoice(9, 1, reason='Cargo adicional')

        self.assertEqual(doc.status, 'accepted')
        adapter.emit_debit_note.assert_called_once()
        self.assertEqual(parent.status, 'accepted')


if __name__ == '__main__':
    unittest.main()
