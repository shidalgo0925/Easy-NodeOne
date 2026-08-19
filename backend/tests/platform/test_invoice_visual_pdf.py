"""Factura visual EN1 + QR FE — tests mínimos (DEV)."""

import sys
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = __import__('pathlib').Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _invoice(**kwargs):
    defaults = dict(
        id=10,
        organization_id=1,
        number='INV-100',
        status='posted',
        date=None,
        due_date=None,
        total=100.0,
        tax_total=7.0,
        grand_total=107.0,
        amount_paid=0.0,
        origin_quotation_id=None,
        customer_id=1,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _org():
    return SimpleNamespace(
        legal_name='Acme Legal S.A.',
        name='Acme',
        tax_id='123456-1-123456',
        fiscal_address='Calle 1',
        fiscal_city='Panamá',
        fiscal_state='',
        fiscal_country='PA',
        fiscal_phone='555-0000',
        fiscal_email='facturacion@acme.test',
    )


def _cfg():
    return {
        'date_format': 'DD/MM/YYYY',
        'time_format': '24h',
        'number_format': '1,234.56',
        'money_decimals': 2,
        'qty_decimals': 2,
        'currency_symbol': '$',
        'symbol_position': 'before',
        'paper_size': 'letter',
    }


class TestPacContractExtract(unittest.TestCase):
    def test_extracts_swagger_create_invoice_fields(self):
        from nodeone.modules.efactura.services.pac_artifacts import extract_pac_artifacts

        raw = {
            'autorizada': True,
            'cufe': 'CUFE-REAL-001',
            'protocoloAutorizacion': 'PROT-99',
            'fechaAutorizacion': '2026-08-19T15:30:00',
            'qrContent': 'https://dgi.example/cufe/CUFE-REAL-001',
            'qrContentImageBase64': 'aGVsbG8=',
            'xml': 'PHhtbD4=',
            'id': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        }
        art = extract_pac_artifacts(raw)
        self.assertEqual(art['cufe'], 'CUFE-REAL-001')
        self.assertEqual(art['protocolo'], 'PROT-99')
        self.assertEqual(art['qr_source'], 'pac_image')
        self.assertEqual(art['qr_content'], 'https://dgi.example/cufe/CUFE-REAL-001')
        self.assertEqual(art['xml_content'], 'PHhtbD4=')
        self.assertEqual(art['pac_document_id'], 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')


class TestFeVisualQrRules(unittest.TestCase):
    def test_no_fe_no_qr(self):
        from nodeone.modules.efactura.services.fe_visual import fiscal_banner_text, should_show_fiscal_qr

        self.assertFalse(should_show_fiscal_qr(None))
        self.assertIn('no autorizada', fiscal_banner_text(None).lower())

    def test_pending_no_qr(self):
        from nodeone.modules.efactura.services.fe_visual import fiscal_banner_text, should_show_fiscal_qr

        fe = SimpleNamespace(status='pending', cufe=None)
        self.assertFalse(should_show_fiscal_qr(fe))
        self.assertIn('pendiente', fiscal_banner_text(fe).lower())

    def test_rejected_no_qr(self):
        from nodeone.modules.efactura.services.fe_visual import fiscal_banner_text, should_show_fiscal_qr

        fe = SimpleNamespace(status='rejected', cufe='')
        self.assertFalse(should_show_fiscal_qr(fe))
        self.assertIn('rechazada', fiscal_banner_text(fe).lower())

    def test_accepted_cufe_shows_qr_of_that_cufe(self):
        from nodeone.modules.efactura.services.fe_visual import resolve_qr_payload, should_show_fiscal_qr

        fe = SimpleNamespace(
            status='accepted',
            cufe='CUFE-XYZ-777',
            qr_image_base64=None,
            qr_content='CUFE-XYZ-777',
            qr_url=None,
            consultation_url=None,
        )
        self.assertTrue(should_show_fiscal_qr(fe))
        img, payload, source = resolve_qr_payload(fe)
        self.assertIsNone(img)
        self.assertEqual(payload, 'CUFE-XYZ-777')
        self.assertEqual(source, 'pac_content')

    def test_qr_not_reused_from_other_cufe(self):
        from nodeone.modules.efactura.services.fe_visual import resolve_qr_payload

        fe_a = SimpleNamespace(
            status='accepted',
            cufe='CUFE-A',
            qr_image_base64=None,
            qr_content='CUFE-A',
            qr_url=None,
            consultation_url=None,
        )
        fe_b = SimpleNamespace(
            status='accepted',
            cufe='CUFE-B',
            qr_image_base64=None,
            qr_content='CUFE-B',
            qr_url=None,
            consultation_url=None,
        )
        self.assertEqual(resolve_qr_payload(fe_a)[1], 'CUFE-A')
        self.assertEqual(resolve_qr_payload(fe_b)[1], 'CUFE-B')
        self.assertNotEqual(resolve_qr_payload(fe_a)[1], resolve_qr_payload(fe_b)[1])


class TestInvoiceVisualPdf(unittest.TestCase):
    def _ctx(self, invoice, fe=None, **extra):
        from nodeone.modules.accounting.invoice_pdf import build_invoice_visual_context

        lines = extra.pop(
            'lines',
            [{'description': 'Servicio', 'is_note': False, 'quantity': 1, 'price_unit': 100, 'tax_amount': 7, 'total': 107}],
        )
        return build_invoice_visual_context(
            invoice,
            fe=fe,
            org=_org(),
            customer={
                'name': 'Cliente Demo',
                'tax_id': '8-1',
                'dv': '23',
                'address': 'Vía España',
                'phone': '6000',
                'email': 'c@demo.test',
            },
            lines=lines,
            cfg=_cfg(),
            **extra,
        )

    def test_pdf_without_fe_has_banner_no_qr(self):
        from nodeone.modules.accounting.invoice_pdf import render_invoice_pdf_from_context

        ctx = self._ctx(_invoice())
        self.assertFalse(ctx['show_qr'])
        self.assertIn('no autorizada', ctx['fe_banner'].lower())
        with patch('nodeone.modules.accounting.invoice_pdf._logo_path', return_value=None):
            pdf = render_invoice_pdf_from_context(ctx)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 500)

    def test_pending_and_rejected_no_qr_distinct_copy(self):
        pending = self._ctx(_invoice(), fe=SimpleNamespace(status='pending', cufe=None, pac_reference=None, authorized_at=None, accepted_at=None))
        rejected = self._ctx(_invoice(), fe=SimpleNamespace(status='rejected', cufe='', pac_reference=None, authorized_at=None, accepted_at=None))
        self.assertFalse(pending['show_qr'])
        self.assertFalse(rejected['show_qr'])
        self.assertNotEqual(pending['fe_banner'], rejected['fe_banner'])
        self.assertIn('pendiente', pending['fe_banner'].lower())
        self.assertIn('rechazada', rejected['fe_banner'].lower())

    def test_accepted_pdf_has_qr_and_cufe(self):
        from nodeone.modules.accounting.invoice_pdf import render_invoice_pdf_from_context

        fe = SimpleNamespace(
            status='accepted',
            cufe='CUFE-ACEPTADA-42',
            qr_image_base64=None,
            qr_content='CUFE-ACEPTADA-42',
            qr_url=None,
            consultation_url=None,
            pac_reference='PROT-1',
            authorized_at=None,
            accepted_at=None,
        )
        ctx = self._ctx(_invoice(), fe=fe)
        self.assertTrue(ctx['show_qr'])
        self.assertEqual(ctx['qr_payload'], 'CUFE-ACEPTADA-42')
        self.assertEqual(ctx['org_legal_name'], 'Acme Legal S.A.')
        self.assertEqual(ctx['grand_total'], 107.0)
        with patch('nodeone.modules.accounting.invoice_pdf._logo_path', return_value=None):
            pdf = render_invoice_pdf_from_context(ctx)
        self.assertTrue(pdf.startswith(b'%PDF'))
        self._assert_qr_decodable(ctx['qr_payload'])

    def _assert_qr_decodable(self, payload: str):
        import qrcode

        qr = qrcode.QRCode(border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        png = buf.getvalue()
        self.assertGreater(len(png), 100)
        try:
            from pyzbar.pyzbar import decode as zbar_decode
            from PIL import Image
        except Exception:
            return
        decoded = zbar_decode(Image.open(BytesIO(png)))
        texts = [d.data.decode('utf-8') for d in decoded]
        self.assertIn(payload, texts)

    def test_totals_match_invoice_not_recalculated(self):
        inv = _invoice(total=50.0, tax_total=3.5, grand_total=53.5, amount_paid=53.5)
        ctx = self._ctx(inv)
        self.assertEqual(ctx['subtotal'], 50.0)
        self.assertEqual(ctx['tax_total'], 3.5)
        self.assertEqual(ctx['grand_total'], 53.5)
        self.assertEqual(ctx['amount_due'], 0.0)

    def test_header_uses_emitting_org_not_hardcoded_ets(self):
        ctx = self._ctx(_invoice())
        blob = f"{ctx['org_legal_name']} {ctx['org_tax_id']}".lower()
        self.assertNotIn('easy technology services', blob)
        self.assertIn('acme legal', blob)

    def test_xls_quotation_origin_uses_same_generator(self):
        from nodeone.modules.accounting.invoice_pdf import render_invoice_pdf_from_context

        ctx_a = self._ctx(_invoice(origin_quotation_id=None))
        ctx_b = self._ctx(_invoice(origin_quotation_id=99))
        with patch('nodeone.modules.accounting.invoice_pdf._logo_path', return_value=None):
            pdf_a = render_invoice_pdf_from_context(ctx_a)
            pdf_b = render_invoice_pdf_from_context(ctx_b)
        self.assertTrue(pdf_a.startswith(b'%PDF'))
        self.assertTrue(pdf_b.startswith(b'%PDF'))
        self.assertEqual(ctx_a['grand_total'], ctx_b['grand_total'])

    def test_regenerate_pdf_does_not_emit_fe(self):
        from nodeone.modules.accounting import invoice_pdf as mod
        from nodeone.modules.accounting.invoice_pdf import render_invoice_pdf_from_context

        ctx = self._ctx(_invoice())
        with patch('nodeone.modules.accounting.invoice_pdf._logo_path', return_value=None):
            with patch.object(mod, 'find_latest_fe_for_invoice') as mock_fe:
                render_invoice_pdf_from_context(ctx)
                mock_fe.assert_not_called()


class TestInvoicePdfTenantIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    def test_pdf_route_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/invoices/<int:iid>/pdf', rules)
        self.assertIn('/invoices/<int:iid>/fe-pac', rules)

    @patch('nodeone.modules.accounting.invoice_pdf.load_invoice_for_visual', return_value=None)
    @patch('nodeone.modules.accounting.routes._can_accounting', return_value=True)
    @patch('nodeone.modules.accounting.routes._org_id', return_value=1)
    @patch('flask_login.utils._get_user')
    def test_other_org_cannot_download_pdf(self, mock_user, _oid, _can, _load):
        user = MagicMock()
        user.is_authenticated = True
        mock_user.return_value = user
        with patch('nodeone.modules.accounting.routes._ensure_tables'):
            resp = self.client.get('/invoices/999/pdf')
        self.assertEqual(resp.status_code, 404)

    @patch('nodeone.modules.accounting.invoice_pdf.render_invoice_pdf_bytes', return_value=b'%PDF-fake')
    @patch('nodeone.modules.accounting.invoice_pdf.load_invoice_for_visual')
    @patch('nodeone.modules.accounting.routes._can_accounting', return_value=True)
    @patch('nodeone.modules.accounting.routes._org_id', return_value=1)
    @patch('flask_login.utils._get_user')
    def test_pdf_route_does_not_call_issue(self, mock_user, _oid, _can, mock_load, mock_render):
        user = MagicMock()
        user.is_authenticated = True
        mock_user.return_value = user
        mock_load.return_value = _invoice()
        with patch('nodeone.modules.accounting.routes._ensure_tables'):
            with patch('nodeone.modules.efactura.services.issue.issue_test_invoice') as mock_issue:
                resp = self.client.get('/invoices/10/pdf')
        self.assertEqual(resp.status_code, 200)
        mock_issue.assert_not_called()
        mock_render.assert_called_once()


if __name__ == '__main__':
    unittest.main()
