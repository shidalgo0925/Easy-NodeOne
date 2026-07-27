"""
Bloque comercio EPosOne — test integrado de registro (sesión jul 2026).

Cubre en un solo módulo los slices desplegados en develop:
  - GET /api/eposone/contacts + sync contactos
  - transfer_order (§6.4 transferencia a caja)
  - credit_note en reembolso total con fiscal invoiced
  - UI back office: pedidos, detalle, clientes nativos

Ejecutar:
  cd backend && pytest tests/platform/test_eposone_commerce_block.py -v
  cd backend && pytest tests/platform/ -q   # suite completa
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEPosOneCommerceBlockRegistry(unittest.TestCase):
    """Rutas API, sync offline y secciones UI del bloque."""

    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_sync_operations_block_catalog(self):
        from nodeone.modules.eposone.sync_handlers import EPOSONE_SYNC_OPERATIONS

        required = frozenset(
            {
                'create_order',
                'transition_order_status',
                'capture_payment',
                'refund_payment',
                'split_order',
                'transfer_order',
                'stock_adjust',
                'create_contact',
                'promote_legacy_contact',
            }
        )
        self.assertTrue(required.issubset(EPOSONE_SYNC_OPERATIONS))

    def test_api_routes_block_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        for path in (
            '/api/eposone/contacts',
            '/api/eposone/contacts/<int:contact_id>',
            '/api/eposone/contacts/resolve/<int:contact_id>',
            '/api/eposone/orders/<int:order_id>/transfer',
            '/api/eposone/orders/<int:order_id>/split',
            '/api/eposone/stock-adjust',
        ):
            self.assertIn(path, rules)

    def test_ui_routes_block_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/admin/eposone/section/<slug>', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>', rules)
        self.assertIn('/admin/eposone/dashboard', rules)
        self.assertIn('/admin/eposone/orders/new', rules)
        self.assertIn('/admin/eposone/contacts/create', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>/status', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>/capture-payment', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>/transfer', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>/emit-fiscal', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>/refund-payment', rules)
        self.assertIn('/admin/eposone/orders/<int:order_id>/apply-promotion', rules)
        self.assertIn('/admin/eposone/registers/open', rules)
        self.assertIn('/admin/eposone/registers/<int:shift_id>/reconcile', rules)
        self.assertIn('/admin/eposone/registers/<int:shift_id>/close', rules)
        self.assertIn('/admin/eposone/shifts/<int:shift_id>/movement', rules)
        self.assertIn('/admin/eposone/kds/<int:ticket_id>/status', rules)
        self.assertIn('/admin/eposone/delivery/<int:delivery_id>/assign', rules)
        self.assertIn('/admin/eposone/delivery/<int:delivery_id>/status', rules)
        self.assertIn('/admin/eposone/digital-menus/create', rules)
        self.assertIn('/admin/eposone/digital-menus/<int:menu_id>/active', rules)
        self.assertIn('/admin/eposone/promotions/create', rules)
        self.assertIn('/admin/eposone/promotions/<int:promotion_id>/active', rules)
        self.assertIn('/api/eposone/promotions', rules)
        self.assertIn('/api/eposone/orders/<int:order_id>/apply-promotion', rules)
        self.assertIn('/admin/eposone/settings/save', rules)
        self.assertIn('/api/eposone/settings', rules)

    def test_credit_note_event_in_commerce_types(self):
        from nodeone.core.commerce.events import COMMERCE_CREDIT_NOTE_REQUESTED, COMMERCE_EVENT_TYPES

        self.assertIn(COMMERCE_CREDIT_NOTE_REQUESTED, COMMERCE_EVENT_TYPES)

    def test_order_dto_exposes_discount_fields(self):
        from nodeone.core.commerce.dtos import OrderDTO
        from datetime import datetime

        dto = OrderDTO(
            id=1,
            organization_id=1,
            order_ref='POS-0001',
            status='ready',
            payment_status='unpaid',
            fiscal_status='not_required',
            contact_id=None,
            currency='USD',
            subtotal=100.0,
            tax_total=0.0,
            grand_total=80.0,
            amount_paid=0.0,
            lines=(),
            source_app_id='eposone',
            discount_total=20.0,
            promotion_ref='PROMO-0001',
            created_at=datetime.utcnow(),
        )
        d = dto.to_dict()
        self.assertEqual(d['discount_total'], 20.0)
        self.assertEqual(d['promotion_ref'], 'PROMO-0001')
        self.assertEqual(d['grand_total'], 80.0)

    def test_order_dto_exposes_terminal_id(self):
        from nodeone.core.commerce.dtos import OrderDTO
        from datetime import datetime

        dto = OrderDTO(
            id=1,
            organization_id=1,
            order_ref='POS-0001',
            status='ready',
            payment_status='unpaid',
            fiscal_status='not_required',
            contact_id=None,
            currency='USD',
            subtotal=10.0,
            tax_total=0.0,
            grand_total=10.0,
            amount_paid=0.0,
            lines=(),
            source_app_id='eposone',
            pos_terminal_id=7,
            created_at=datetime.utcnow(),
        )
        d = dto.to_dict()
        self.assertEqual(d['terminal_id'], 7)
        self.assertEqual(d['pos_terminal_id'], 7)


class TestEPosOneBackOfficeCreate(unittest.TestCase):
    """UI back office — crear cliente y pedido desde formularios HTML."""

    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.services.contacts.ContactService.create')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_contact_create_redirects(self, _oid, mock_create, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_create.return_value = SimpleNamespace(id=9, display_name='Ana POS')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_contact_create')
        resp = self.client.post(
            action,
            data={
                'display_name': 'Ana POS',
                'contact_type': 'person',
                'is_customer': '1',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_create.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.order.OrderService.create')
    @patch('nodeone.core.services.product.ProductService.search', return_value=[])
    @patch('nodeone.core.services.contacts.ContactService.search', return_value=([], 0))
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_order_new_post_creates(self, _oid, _contacts, _products, mock_create, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_create.return_value = SimpleNamespace(id=12, order_ref='POS-0012')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_order_new')
        resp = self.client.post(
            action,
            data={
                'description': 'Café',
                'quantity': '2',
                'unit_price': '3.50',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_create.assert_called_once()


class TestEPosOneOrderDetailActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.order.OrderService.transition_status')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_order_status_post(self, _oid, mock_transition, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_transition.return_value = SimpleNamespace(status='confirmed')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_order_status', order_id=5)
        resp = self.client.post(action, data={'status': 'confirmed'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_transition.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.payment.PaymentService.capture')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_order_capture_payment_post(self, _oid, mock_capture, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_capture.return_value = SimpleNamespace(payment_ref='PAY-0001', amount=10.0)
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_order_capture_payment', order_id=5)
        resp = self.client.post(
            action,
            data={'amount': '10.00', 'payment_type': 'card'},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_capture.assert_called_once()


class TestEPosOneOrderFiscalRefund(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService.process_pending_order')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_order_emit_fiscal_post(self, _oid, mock_fiscal, _gate, mock_get_user):
        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_fiscal.return_value = {'status': 'issued', 'order_ref': 'POS-0001'}
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_order_emit_fiscal', order_id=5)
        resp = self.client.post(action, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_fiscal.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.payment.PaymentService.refund')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_order_refund_payment_post(self, _oid, mock_refund, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        user.id = 99
        mock_get_user.return_value = user
        mock_refund.return_value = SimpleNamespace(payment_ref='PAY-0009')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_order_refund_payment', order_id=5)
        resp = self.client.post(
            action,
            data={'payment_id': '9', 'amount': '10.00', 'supervisor_user_id': '99'},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_refund.assert_called_once()


class TestEPosOneRegistersActions(unittest.TestCase):
    """UI back office — apertura, arqueo y cierre de turnos de caja."""

    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.routes._cashier_from_form')
    @patch('nodeone.core.commerce.cash.CashRegisterService.open_shift')
    @patch('models.commercial_core.CorePosTerminal')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_register_open_shift_post(
        self, _oid, mock_terminal_cls, mock_open, _cashier, _gate, mock_get_user
    ):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        _cashier.return_value = SimpleNamespace(id=7, display_name='Ana Pérez')
        mock_terminal_cls.query.filter_by.return_value.first.return_value = SimpleNamespace()
        mock_open.return_value = SimpleNamespace(
            register_ref='REG-1',
            opening_balance=100.0,
            cashier_name='Ana Pérez',
        )
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_register_open_shift')
        resp = self.client.post(
            action,
            data={'register_ref': 'REG-1', 'opening_balance': '100.00', 'cashier_contact_id': '7'},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_open.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.routes._cashier_from_form')
    @patch('nodeone.core.commerce.cash.CashRegisterService.change_cashier')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_register_change_cashier_post(
        self, _oid, mock_change, _cashier, _gate, mock_get_user
    ):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        user.id = 99
        mock_get_user.return_value = user
        _cashier.return_value = SimpleNamespace(id=8, display_name='Luis Gómez')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_register_change_cashier', shift_id=3)
        resp = self.client.post(
            action,
            data={'cashier_contact_id': '8'},
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_change.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.cash.CashRegisterService.begin_reconcile')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_register_reconcile_shift_post(self, _oid, mock_reconcile, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_reconcile.return_value = SimpleNamespace(register_ref='REG-1')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_register_reconcile_shift', shift_id=3)
        resp = self.client.post(action, data={'counted_amount': '150.00'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_reconcile.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.cash.CashRegisterService.close_shift')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_register_close_shift_post(self, _oid, mock_close, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_close.return_value = SimpleNamespace(register_ref='REG-1', cash_variance=0.0)
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_register_close_shift', shift_id=3)
        resp = self.client.post(action, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_close.assert_called_once()


class TestEPosOneShiftsActions(unittest.TestCase):
    """UI back office — turnos de caja y movimientos manuales."""

    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.core.commerce.cash.CashRegisterService.record_manual_movement')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_shift_movement_post(self, _oid, mock_movement, _gate, mock_get_user):
        user = MagicMock()
        user.is_authenticated = True
        user.id = 42
        mock_get_user.return_value = user
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_shift_movement', shift_id=5)
        resp = self.client.post(
            action,
            data={
                'movement_type': 'cash_in',
                'amount': '25.00',
                'supervisor_user_id': '42',
                'reason': 'Fondo cambio',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_movement.assert_called_once()


class TestEPosOneKdsDeliveryActions(unittest.TestCase):
    """UI back office — KDS y delivery transaccionales."""

    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.kds_service.KdsService.transition_ticket')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_kds_ticket_status_post(self, _oid, mock_transition, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_transition.return_value = SimpleNamespace(order_ref='POS-0001', status='preparing')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_kds_ticket_status', ticket_id=7)
        resp = self.client.post(action, data={'status': 'preparing'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_transition.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.delivery_service.EposoneDeliveryService.assign_driver')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_delivery_assign_post(self, _oid, mock_assign, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_assign.return_value = SimpleNamespace(order_ref='POS-0002')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_delivery_assign', delivery_id=3)
        resp = self.client.post(action, data={'driver_name': 'Juan'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_assign.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.delivery_service.EposoneDeliveryService.transition_status')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_delivery_status_post(self, _oid, mock_transition, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_transition.return_value = SimpleNamespace(order_ref='POS-0002', status='in_transit')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_delivery_status', delivery_id=3)
        resp = self.client.post(action, data={'status': 'in_transit'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_transition.assert_called_once()


class TestEPosOneDigitalMenuActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.digital_menu_service.DigitalMenuService.create_menu')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_digital_menu_create_post(self, _oid, mock_create, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_create.return_value = SimpleNamespace(menu_ref='MENU-0001', items=(SimpleNamespace(),))
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_digital_menu_create')
        resp = self.client.post(
            action,
            data={
                'name': 'Almuerzo',
                'item_name': ['Sopa', ''],
                'item_price': ['5.50', ''],
                'item_category': ['Entradas', ''],
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        self.assertEqual(call_kwargs[0][0], 1)
        self.assertEqual(call_kwargs[1]['name'], 'Almuerzo')
        self.assertEqual(len(call_kwargs[1]['items']), 1)

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.digital_menu_service.DigitalMenuService.set_active')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_digital_menu_set_active_post(self, _oid, mock_set_active, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_set_active.return_value = SimpleNamespace(menu_ref='MENU-0001', active=False)
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_digital_menu_set_active', menu_id=4)
        resp = self.client.post(action, data={'active': '0'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_set_active.assert_called_once_with(1, 4, active=False)


class TestEPosOnePromotionActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.promotion_service.PromotionService.create_promotion')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_promotion_create_post(self, _oid, mock_create, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_create.return_value = SimpleNamespace(promo_ref='PROMO-0001')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_promotion_create')
        resp = self.client.post(
            action,
            data={
                'name': 'Happy hour',
                'promo_type': 'percent',
                'value': '15',
                'code': 'HAPPY15',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        mock_create.assert_called_once()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.promotion_service.PromotionService.set_active')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_promotion_set_active_post(self, _oid, mock_set_active, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_set_active.return_value = SimpleNamespace(promo_ref='PROMO-0001', active=True)
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_promotion_set_active', promotion_id=2)
        resp = self.client.post(action, data={'active': '1'}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        mock_set_active.assert_called_once_with(1, 2, active=True)


class TestEPosOneSettingsActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    @patch('flask_login.utils._get_user')
    @patch('nodeone.modules.eposone.routes.user_can_see_tenant_admin_menu', return_value=True)
    @patch('nodeone.modules.eposone.settings_service.EposoneSettingsService.update_settings')
    @patch('nodeone.core.platform.runtime.resolve_organization_id', return_value=1)
    def test_settings_save_post(self, _oid, mock_update, _gate, mock_get_user):
        from types import SimpleNamespace

        user = MagicMock()
        user.is_authenticated = True
        mock_get_user.return_value = user
        mock_update.return_value = SimpleNamespace(default_currency='PAB')
        with self.app.test_request_context():
            from flask import url_for

            action = url_for('eposone.eposone_settings_save')
        resp = self.client.post(
            action,
            data={
                'settings_panel': 'kds',
                'redirect_slug': 'kds',
                'kds_auto_enqueue': '1',
                'delivery_auto_create': '1',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/admin/eposone/section/kds', resp.headers.get('Location', ''))
        mock_update.assert_called_once()
        kwargs = mock_update.call_args.kwargs
        self.assertTrue(kwargs.get('kds_auto_enqueue'))
        self.assertTrue(kwargs.get('delivery_auto_create'))
        self.assertNotIn('default_currency', kwargs)


class TestEPosOneDashboardKpis(unittest.TestCase):
    @patch('nodeone.core.commerce.dashboard.CoreStockBalance')
    @patch('nodeone.core.commerce.dashboard.CoreCashShift')
    @patch('nodeone.core.commerce.dashboard.CoreCommercialPayment')
    @patch('nodeone.core.commerce.dashboard.CoreCommercialOrder')
    def test_dashboard_snapshot_aggregates(self, mock_order_cls, mock_pay_cls, mock_shift_cls, mock_stock_cls):
        from nodeone.core.commerce.dashboard import CommerceDashboardService

        col = MagicMock()
        col.__ge__ = MagicMock(return_value=MagicMock())
        col.__lt__ = MagicMock(return_value=MagicMock())
        mock_order_cls.organization_id = col
        mock_order_cls.created_at = col
        mock_pay_cls.organization_id = col
        mock_pay_cls.status = col
        mock_pay_cls.captured_at = col

        mock_order_cls.query.filter.return_value.count.return_value = 3
        mock_order_cls.query.filter_by.return_value.order_by.return_value.first.return_value = SimpleNamespace(
            currency='USD'
        )

        pay_q = mock_pay_cls.query.filter.return_value
        pay_q.with_entities.return_value.scalar.return_value = 125.5

        mock_shift_cls.query.filter_by.return_value.count.return_value = 2

        mock_stock_cls.query.filter_by.return_value.all.return_value = [
            SimpleNamespace(quantity_on_hand=0, quantity_reserved=0),
            SimpleNamespace(quantity_on_hand=5, quantity_reserved=1),
        ]

        snap = CommerceDashboardService.get_snapshot(42)
        self.assertEqual(snap.orders_today, 3)
        self.assertEqual(snap.sales_today, 125.5)
        self.assertEqual(snap.open_registers, 2)
        self.assertEqual(snap.stock_alerts, 1)
        self.assertEqual(snap.currency, 'USD')


class TestEPosOneCommerceBlockFlow(unittest.TestCase):
    """Flujo encadenado (mocks) — pedido → transfer → reembolso facturado."""

    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService.request_credit_note_for_order')
    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_invoiced_full_refund_triggers_credit_note(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        _supervisor,
        mock_credit_note,
        _payment_changed,
        _fiscal_changed,
        _status_changed,
        _refunded,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_FISCAL_STATUS_CANCELLED,
            ORDER_FISCAL_STATUS_INVOICED,
            ORDER_STATUS_DELIVERED,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 20
        order.order_ref = 'POS-0020'
        order.status = ORDER_STATUS_DELIVERED
        order.payment_status = 'paid'
        order.fiscal_status = ORDER_FISCAL_STATUS_INVOICED
        order.amount_paid = 30.0
        order.version = 1
        order.sync_payment_status.return_value = 'unpaid'

        pay = MagicMock()
        pay.id = 9
        pay.order_id = 20
        pay.payment_ref = 'PAY-0020'
        pay.status = 'captured'
        pay.amount = 30.0
        pay.refunded_amount = 0.0
        pay.payment_type = 'card'
        pay.cash_shift_id = None
        pay.currency = 'USD'

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay
        mock_order_cls.query.filter_by.return_value.first.return_value = order
        mock_credit_note.return_value = {'status': 'queued'}

        PaymentService.refund(1, 9, approval={'supervisor_user_id': 1})

        mock_credit_note.assert_called_once()
        self.assertEqual(order.fiscal_status, ORDER_FISCAL_STATUS_CANCELLED)

    @patch('nodeone.core.commerce.order.OrderService.publish_transferred')
    @patch('app.db')
    @patch('nodeone.core.commerce.pos.PosTerminalService.get')
    @patch('nodeone.core.commerce.pos.PosTerminalService.resolve_id', return_value=3)
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_transfer_then_ready_for_cashier(
        self,
        mock_order_cls,
        _resolve,
        mock_terminal_get,
        mock_db,
        _published,
    ):
        from nodeone.core.commerce.dtos import PosTerminalDTO
        from nodeone.core.commerce.order import OrderService

        row = MagicMock()
        row.id = 8
        row.organization_id = 1
        row.order_ref = 'POS-0008'
        row.payment_status = 'unpaid'
        row.operational_status = 'ready'
        row.pos_terminal_id = 1
        row.version = 1
        row.contact_id = None
        row.branch_org_unit_id = None
        row.parent_order_id = None
        row.currency = 'USD'
        row.fiscal_status = 'not_required'
        row.subtotal = 15.0
        row.tax_total = 0.0
        row.grand_total = 15.0
        row.amount_paid = 0.0
        row.source_app_id = 'eposone'
        row.created_at = None
        row.lines = []
        mock_order_cls.query.filter_by.return_value.first.return_value = row
        mock_terminal_get.return_value = PosTerminalDTO(
            id=3,
            organization_id=1,
            terminal_ref='CAJA-01',
            register_ref='REG-1',
            status='active',
            device_label=None,
        )

        dto = OrderService.transfer_to_terminal(1, 8, {'terminal_ref': 'CAJA-01'})
        self.assertEqual(dto.pos_terminal_id, 3)
        self.assertEqual(row.pos_terminal_id, 3)

    @patch('nodeone.modules.eposone.cashier_service.CashierService.require_cashier')
    @patch('nodeone.modules.eposone.sync_handlers.OrderService.transfer_to_terminal')
    def test_sync_applies_transfer_operation(self, mock_transfer, mock_require_cashier):
        from nodeone.core.sync.queue import SyncOperationDTO
        from nodeone.modules.eposone.sync_handlers import apply_eposone_sync_operation

        mock_require_cashier.return_value = SimpleNamespace(id=27, display_name='Juan Pérez')
        dto = SyncOperationDTO(
            id=99,
            organization_id=1,
            client_id='t1',
            idempotency_key='block-transfer',
            operation_type='transfer_order',
            status='pending',
            entity_type='order',
            entity_ref='POS-0008',
            payload={
                'order_id': 8,
                'terminal_ref': 'CAJA-01',
                'cashier_contact_id': 27,
            },
            base_version=2,
            retry_count=0,
            conflict_reason=None,
            created_at=None,
            applied_at=None,
        )
        apply_eposone_sync_operation(dto)
        mock_transfer.assert_called_once()


if __name__ == '__main__':
    unittest.main()
