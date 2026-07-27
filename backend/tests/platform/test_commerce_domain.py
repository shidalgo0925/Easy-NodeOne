"""Tests dominio comercial — Etapa 12."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCommerceConstants(unittest.TestCase):
    def test_order_transitions(self):
        from nodeone.core.commerce.constants import (
            ORDER_STATUS_CANCELLED,
            ORDER_STATUS_CONFIRMED,
            ORDER_STATUS_DRAFT,
            ORDER_STATUS_DELIVERED,
            ORDER_STATUS_IN_PROGRESS,
            can_transition_order_status,
        )

        self.assertTrue(can_transition_order_status(ORDER_STATUS_DRAFT, ORDER_STATUS_CONFIRMED))
        self.assertTrue(
            can_transition_order_status(ORDER_STATUS_CONFIRMED, ORDER_STATUS_IN_PROGRESS)
        )
        self.assertFalse(can_transition_order_status(ORDER_STATUS_DRAFT, ORDER_STATUS_DELIVERED))
        self.assertFalse(can_transition_order_status(ORDER_STATUS_CANCELLED, ORDER_STATUS_CONFIRMED))

    def test_commerce_event_types_complete(self):
        from nodeone.core.commerce import events as ev

        self.assertIn(ev.COMMERCE_ORDER_CREATED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_PAYMENT_CAPTURED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_ORDER_PAYMENT_STATUS_CHANGED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_ORDER_FISCAL_STATUS_CHANGED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_INVOICE_REQUESTED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_CASH_MOVEMENT_RECORDED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_CASH_SHIFT_RECONCILING, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_AUTHORIZATION_APPLIED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_INVENTORY_RESERVED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_INVENTORY_DEDUCTED, ev.COMMERCE_EVENT_TYPES)
        self.assertIn(ev.COMMERCE_REPORT_SALE_RECORDED, ev.COMMERCE_EVENT_TYPES)

    def test_inventory_policy_helpers(self):
        from nodeone.core.commerce.constants import (
            INVENTORY_POLICY_CONSIGNMENT,
            INVENTORY_POLICY_DISPATCH_REQUIRED,
            INVENTORY_POLICY_NONE,
            INVENTORY_POLICY_RETAIL_STANDARD,
            inventory_policy_deducts_on_delivered,
            inventory_policy_deducts_on_paid,
            inventory_policy_reserves_on_confirmed,
        )

        self.assertTrue(inventory_policy_reserves_on_confirmed(INVENTORY_POLICY_RETAIL_STANDARD))
        self.assertFalse(inventory_policy_reserves_on_confirmed(INVENTORY_POLICY_NONE))
        self.assertTrue(inventory_policy_deducts_on_paid(INVENTORY_POLICY_RETAIL_STANDARD))
        self.assertFalse(inventory_policy_deducts_on_paid(INVENTORY_POLICY_DISPATCH_REQUIRED))
        self.assertTrue(inventory_policy_deducts_on_delivered(INVENTORY_POLICY_DISPATCH_REQUIRED))
        self.assertTrue(inventory_policy_deducts_on_delivered(INVENTORY_POLICY_CONSIGNMENT))
        self.assertFalse(inventory_policy_deducts_on_delivered(INVENTORY_POLICY_RETAIL_STANDARD))

    def test_compute_order_payment_status(self):
        from nodeone.core.commerce.constants import (
            ORDER_PAYMENT_STATUS_OVERPAID,
            ORDER_PAYMENT_STATUS_PAID,
            ORDER_PAYMENT_STATUS_PARTIAL,
            ORDER_PAYMENT_STATUS_UNPAID,
            compute_order_payment_status,
        )

        self.assertEqual(compute_order_payment_status(0, 10), ORDER_PAYMENT_STATUS_UNPAID)
        self.assertEqual(compute_order_payment_status(5, 10), ORDER_PAYMENT_STATUS_PARTIAL)
        self.assertEqual(compute_order_payment_status(10, 10), ORDER_PAYMENT_STATUS_PAID)
        self.assertEqual(compute_order_payment_status(12, 10), ORDER_PAYMENT_STATUS_OVERPAID)

    def test_order_model_status_alias(self):
        from models.commercial_core import CoreCommercialOrder

        row = CoreCommercialOrder()
        row.operational_status = 'confirmed'
        self.assertEqual(row.status, 'confirmed')
        row.status = 'in_progress'
        self.assertEqual(row.operational_status, 'in_progress')


class TestPaymentServiceAxis(unittest.TestCase):
    @patch('nodeone.modules.eposone.settings_service.EposoneSettingsService.runtime_for')
    @patch('nodeone.core.commerce.cash.CashRegisterService.record_movement')
    @patch('nodeone.core.commerce.cash.CashRegisterService.require_open_shift')
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_captured')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_initiated')
    @patch('nodeone.core.commerce.payment.PaymentService._next_payment_ref', return_value='PAY-0001')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_capture_updates_payment_status_not_operational(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        _next_ref,
        mock_initiated,
        mock_captured,
        mock_payment_changed,
        mock_fiscal_changed,
        mock_require_shift,
        mock_record_movement,
        mock_runtime,
    ):
        from types import SimpleNamespace

        from nodeone.core.commerce.constants import ORDER_PAYMENT_STATUS_PAID, ORDER_STATUS_IN_PROGRESS
        from nodeone.core.commerce.payment import PaymentService

        mock_runtime.return_value = SimpleNamespace(fiscal_on_payment=True)

        shift = MagicMock()
        shift.id = 3
        mock_require_shift.return_value = shift

        order = MagicMock()
        order.id = 7
        order.order_ref = 'POS-0001'
        order.status = ORDER_STATUS_IN_PROGRESS
        order.payment_status = 'unpaid'
        order.fiscal_status = 'not_required'
        order.amount_paid = 0.0
        order.grand_total = 10.0
        order.currency = 'USD'
        order.version = 1

        def _sync():
            order.payment_status = ORDER_PAYMENT_STATUS_PAID
            return ORDER_PAYMENT_STATUS_PAID

        order.sync_payment_status.side_effect = _sync

        def _fiscal(*, skip_fiscal=False):
            if skip_fiscal:
                return None
            order.fiscal_status = 'pending'
            return 'not_required'

        order.maybe_mark_fiscal_pending.side_effect = _fiscal
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        pay_row = MagicMock()
        pay_row.id = 1
        pay_row.organization_id = 1
        pay_row.payment_ref = 'PAY-0001'
        pay_row.status = 'captured'
        pay_row.payment_type = 'cash'
        pay_row.amount = 10.0
        pay_row.currency = 'USD'
        pay_row.captured_at = None
        mock_payment_cls.return_value = pay_row

        PaymentService.capture(1, {'order_id': 7, 'amount': 10, 'register_ref': 'REG-1'})

        self.assertEqual(order.status, ORDER_STATUS_IN_PROGRESS)
        mock_payment_changed.assert_called_once()
        mock_fiscal_changed.assert_called_once()

    @patch('nodeone.core.commerce.cash.CashRegisterService.record_movement')
    @patch('nodeone.core.commerce.cash.CashRegisterService.require_open_shift')
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_captured')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_initiated')
    @patch('nodeone.core.commerce.payment.PaymentService._next_payment_ref', return_value='PAY-0002')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_capture_skip_fiscal_opt_out(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        _next_ref,
        mock_initiated,
        mock_captured,
        mock_payment_changed,
        mock_fiscal_changed,
        mock_require_shift,
        mock_record_movement,
    ):
        from nodeone.core.commerce.constants import ORDER_PAYMENT_STATUS_PAID
        from nodeone.core.commerce.payment import PaymentService

        shift = MagicMock()
        shift.id = 4
        mock_require_shift.return_value = shift

        order = MagicMock()
        order.id = 8
        order.order_ref = 'POS-0002'
        order.status = 'confirmed'
        order.payment_status = 'unpaid'
        order.fiscal_status = 'not_required'
        order.amount_paid = 0.0
        order.grand_total = 5.0
        order.currency = 'USD'
        order.version = 1
        order.sync_payment_status.return_value = ORDER_PAYMENT_STATUS_PAID
        order.maybe_mark_fiscal_pending.return_value = None
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        pay_row = MagicMock()
        pay_row.payment_ref = 'PAY-0002'
        pay_row.status = 'captured'
        pay_row.payment_type = 'cash'
        pay_row.amount = 5.0
        pay_row.currency = 'USD'
        pay_row.captured_at = None
        mock_payment_cls.return_value = pay_row

        PaymentService.capture(
            1,
            {'order_id': 8, 'amount': 5, 'skip_fiscal': True, 'register_ref': 'REG-1'},
        )

        order.maybe_mark_fiscal_pending.assert_called_once_with(skip_fiscal=True)
        mock_fiscal_changed.assert_not_called()


class TestPaymentRefund(unittest.TestCase):
    _approval = {'supervisor_user_id': 100}

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_refund_full_reverts_payment_and_order_axes(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_payment_changed,
        mock_fiscal_changed,
        mock_status_changed,
        mock_refunded,
        mock_supervisor,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_FISCAL_STATUS_NOT_REQUIRED,
            ORDER_FISCAL_STATUS_PENDING,
            ORDER_PAYMENT_STATUS_PAID,
            ORDER_PAYMENT_STATUS_UNPAID,
            ORDER_STATUS_DELIVERED,
            ORDER_STATUS_REFUNDED,
            PAYMENT_STATUS_REFUNDED,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 10
        order.order_ref = 'POS-0010'
        order.status = ORDER_STATUS_DELIVERED
        order.payment_status = ORDER_PAYMENT_STATUS_PAID
        order.fiscal_status = ORDER_FISCAL_STATUS_PENDING
        order.amount_paid = 15.0
        order.grand_total = 15.0
        order.version = 1

        def _sync():
            order.payment_status = ORDER_PAYMENT_STATUS_UNPAID
            return ORDER_PAYMENT_STATUS_UNPAID

        order.sync_payment_status.side_effect = _sync

        pay_row = MagicMock()
        pay_row.id = 5
        pay_row.order_id = 10
        pay_row.payment_ref = 'PAY-0010'
        pay_row.status = 'captured'
        pay_row.amount = 15.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = PaymentService.refund(1, 5, approval=self._approval)

        self.assertEqual(pay_row.status, PAYMENT_STATUS_REFUNDED)
        self.assertEqual(order.amount_paid, 0.0)
        self.assertEqual(order.status, ORDER_STATUS_REFUNDED)
        self.assertEqual(order.fiscal_status, ORDER_FISCAL_STATUS_NOT_REQUIRED)
        mock_payment_changed.assert_called_once()
        mock_fiscal_changed.assert_called_once()
        mock_status_changed.assert_called_once()
        mock_refunded.assert_called_once()
        self.assertEqual(result.payment_ref, 'PAY-0010')

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_fiscal_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService.request_credit_note_for_order')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_refund_full_invoiced_requests_credit_note(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_credit_note,
        mock_payment_changed,
        mock_fiscal_changed,
        mock_status_changed,
        mock_refunded,
        mock_supervisor,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_FISCAL_STATUS_CANCELLED,
            ORDER_FISCAL_STATUS_INVOICED,
            ORDER_PAYMENT_STATUS_UNPAID,
            ORDER_STATUS_DELIVERED,
            ORDER_STATUS_REFUNDED,
            PAYMENT_STATUS_REFUNDED,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 12
        order.order_ref = 'POS-0012'
        order.status = ORDER_STATUS_DELIVERED
        order.payment_status = 'paid'
        order.fiscal_status = ORDER_FISCAL_STATUS_INVOICED
        order.amount_paid = 25.0
        order.grand_total = 25.0
        order.version = 1
        order.sync_payment_status.return_value = ORDER_PAYMENT_STATUS_UNPAID

        pay_row = MagicMock()
        pay_row.id = 8
        pay_row.order_id = 12
        pay_row.payment_ref = 'PAY-0012'
        pay_row.status = 'captured'
        pay_row.amount = 25.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order
        mock_credit_note.return_value = {'status': 'queued', 'order_ref': 'POS-0012'}

        PaymentService.refund(1, 8, approval=self._approval)

        self.assertEqual(pay_row.status, PAYMENT_STATUS_REFUNDED)
        self.assertEqual(order.fiscal_status, ORDER_FISCAL_STATUS_CANCELLED)
        self.assertEqual(order.status, ORDER_STATUS_REFUNDED)
        mock_credit_note.assert_called_once()
        mock_fiscal_changed.assert_called_once()

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_refund_partial_does_not_change_operational(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_payment_changed,
        mock_status_changed,
        mock_refunded,
        mock_supervisor,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_PAYMENT_STATUS_PARTIAL,
            ORDER_STATUS_DELIVERED,
            PAYMENT_STATUS_PARTIAL_REFUND,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 11
        order.order_ref = 'POS-0011'
        order.status = ORDER_STATUS_DELIVERED
        order.payment_status = 'paid'
        order.fiscal_status = 'invoiced'
        order.amount_paid = 20.0
        order.grand_total = 20.0
        order.version = 1
        order.sync_payment_status.return_value = ORDER_PAYMENT_STATUS_PARTIAL

        pay_row = MagicMock()
        pay_row.id = 6
        pay_row.order_id = 11
        pay_row.payment_ref = 'PAY-0011'
        pay_row.status = 'captured'
        pay_row.amount = 20.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        PaymentService.refund(1, 6, amount=5.0, approval=self._approval)

        self.assertEqual(pay_row.status, PAYMENT_STATUS_PARTIAL_REFUND)
        self.assertEqual(pay_row.refunded_amount, 5.0)
        self.assertEqual(order.amount_paid, 15.0)
        self.assertEqual(order.status, ORDER_STATUS_DELIVERED)
        mock_status_changed.assert_not_called()
        mock_payment_changed.assert_called_once()
        mock_refunded.assert_called_once()

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    def test_refund_rejects_non_captured(self, mock_payment_cls, mock_supervisor):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.core.commerce.payment import PaymentService

        pay_row = MagicMock()
        pay_row.id = 99
        pay_row.order_id = 1
        pay_row.status = 'refunded'
        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order = MagicMock()
        mock_order.order_ref = 'POS-0099'
        with patch('nodeone.core.commerce.payment.CoreCommercialOrder') as mock_order_cls:
            mock_order_cls.query.filter_by.return_value.first.return_value = mock_order
            with self.assertRaises(OrderValidationError):
                PaymentService.refund(1, 99, approval=self._approval)

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    def test_refund_rejects_when_nothing_left(self, mock_payment_cls, mock_supervisor):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.core.commerce.payment import PaymentService

        pay_row = MagicMock()
        pay_row.id = 50
        pay_row.order_id = 3
        pay_row.status = 'partial_refund'
        pay_row.amount = 10.0
        pay_row.refunded_amount = 10.0
        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row

        with patch('nodeone.core.commerce.payment.CoreCommercialOrder') as mock_order_cls:
            mock_order_cls.query.filter_by.return_value.first.return_value = MagicMock(order_ref='POS-0050')
            with self.assertRaises(OrderValidationError):
                PaymentService.refund(1, 50, amount=1.0, approval=self._approval)

    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor')
    @patch('nodeone.core.commerce.payment.PaymentService.publish_refunded')
    @patch('nodeone.core.commerce.payment.OrderService.publish_status_changed')
    @patch('nodeone.core.commerce.payment.OrderService.publish_payment_status_changed')
    @patch('app.db')
    @patch('nodeone.core.commerce.payment.CoreCommercialPayment')
    @patch('nodeone.core.commerce.payment.CoreCommercialOrder')
    def test_chained_partial_refunds_until_full(
        self,
        mock_order_cls,
        mock_payment_cls,
        mock_db,
        mock_payment_changed,
        mock_status_changed,
        mock_refunded,
        mock_supervisor,
    ):
        from nodeone.core.commerce.constants import (
            ORDER_PAYMENT_STATUS_PAID,
            ORDER_PAYMENT_STATUS_UNPAID,
            PAYMENT_STATUS_PARTIAL_REFUND,
            PAYMENT_STATUS_REFUNDED,
        )
        from nodeone.core.commerce.payment import PaymentService

        order = MagicMock()
        order.id = 12
        order.order_ref = 'POS-0012'
        order.status = 'delivered'
        order.payment_status = ORDER_PAYMENT_STATUS_PAID
        order.fiscal_status = 'not_required'
        order.amount_paid = 20.0
        order.grand_total = 20.0
        order.version = 1

        def _sync():
            order.payment_status = ORDER_PAYMENT_STATUS_UNPAID
            return ORDER_PAYMENT_STATUS_UNPAID

        order.sync_payment_status.side_effect = _sync

        pay_row = MagicMock()
        pay_row.id = 7
        pay_row.order_id = 12
        pay_row.payment_ref = 'PAY-0012'
        pay_row.status = 'captured'
        pay_row.amount = 20.0
        pay_row.refunded_amount = 0.0
        pay_row.payment_type = 'card'
        pay_row.cash_shift_id = None
        pay_row.currency = 'USD'
        pay_row.captured_at = None

        mock_payment_cls.query.filter_by.return_value.first.return_value = pay_row
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        PaymentService.refund(1, 7, amount=8.0, approval=self._approval)
        self.assertEqual(pay_row.refunded_amount, 8.0)
        self.assertEqual(pay_row.status, PAYMENT_STATUS_PARTIAL_REFUND)
        self.assertEqual(order.amount_paid, 12.0)

        PaymentService.refund(1, 7, amount=12.0, approval=self._approval)
        self.assertEqual(pay_row.refunded_amount, 20.0)
        self.assertEqual(pay_row.status, PAYMENT_STATUS_REFUNDED)
        self.assertEqual(order.amount_paid, 0.0)
        self.assertEqual(mock_refunded.call_count, 2)


class TestCommerceAuthorization(unittest.TestCase):
    @patch('nodeone.core.commerce.authorization.AuditService.publish_domain_event')
    @patch('models.users.User')
    def test_assert_supervisor_publishes_event(self, mock_user_cls, mock_publish):
        from nodeone.core.commerce.authorization import CommerceAuthorizationService

        user = MagicMock()
        user.id = 42
        mock_user_cls.query.get.return_value = user

        with patch.object(CommerceAuthorizationService, 'user_is_supervisor', return_value=True):
            uid = CommerceAuthorizationService.assert_supervisor(
                1,
                {'supervisor_user_id': 42, 'reason': 'cliente insatisfecho'},
                action='payment.refund',
                payment_id=9,
            )

        self.assertEqual(uid, 42)
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], 'commerce.authorization.applied')

    def test_supervisor_required_raises(self):
        from nodeone.core.commerce.authorization import CommerceAuthorizationService
        from nodeone.core.commerce.order import OrderValidationError

        with self.assertRaises(OrderValidationError):
            CommerceAuthorizationService.assert_supervisor(1, {}, action='payment.refund')

    def test_user_is_supervisor_platform_admin(self):
        from nodeone.core.commerce.authorization import CommerceAuthorizationService

        user = MagicMock()
        user.id = 1
        user.is_admin = True
        self.assertTrue(CommerceAuthorizationService.user_is_supervisor(user, 99))


class TestCommerceInventoryService(unittest.TestCase):
    @patch('nodeone.core.commerce.inventory.CommerceInventoryService._mark_order_deducted')
    @patch('nodeone.core.commerce.inventory.CommerceInventoryService._order_already_deducted', return_value=False)
    @patch('nodeone.core.commerce.inventory.AuditService.publish_domain_event')
    def test_order_confirmed_publishes_reserved(self, mock_publish, _dedup, _mark):
        from nodeone.core.commerce.events import COMMERCE_INVENTORY_RESERVED, COMMERCE_ORDER_STATUS_CHANGED
        from nodeone.core.commerce.inventory import CommerceInventoryService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=1,
            organization_id=1,
            event_type=COMMERCE_ORDER_STATUS_CHANGED,
            payload={'order_ref': 'POS-0100', 'from_status': 'draft', 'to_status': 'confirmed'},
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceInventoryService.process_order_status_changed(msg)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['movement'], 'reserve')
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_INVENTORY_RESERVED)

    @patch('nodeone.core.commerce.inventory.CommerceInventoryService._mark_order_deducted')
    @patch('nodeone.core.commerce.inventory.CommerceInventoryService._order_already_deducted', return_value=False)
    @patch('nodeone.core.commerce.inventory.AuditService.publish_domain_event')
    def test_payment_paid_publishes_deducted(self, mock_publish, _dedup, mock_mark):
        from nodeone.core.commerce.events import COMMERCE_INVENTORY_DEDUCTED
        from nodeone.core.commerce.inventory import CommerceInventoryService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=2,
            organization_id=1,
            event_type='commerce.order.payment_status_changed',
            payload={
                'order_ref': 'POS-0101',
                'from_payment_status': 'unpaid',
                'to_payment_status': 'paid',
            },
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceInventoryService.process_payment_status_changed(msg)
        self.assertEqual(result['status'], 'published')
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_INVENTORY_DEDUCTED)
        mock_mark.assert_called_once_with(1, 'POS-0101')

    @patch('nodeone.core.commerce.inventory.AuditService.publish_domain_event')
    def test_dispatch_required_skips_deduct_on_paid(self, mock_publish):
        from nodeone.core.commerce.constants import INVENTORY_POLICY_DISPATCH_REQUIRED
        from nodeone.core.commerce.inventory import CommerceInventoryService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=5,
            organization_id=1,
            event_type='commerce.order.payment_status_changed',
            payload={
                'order_ref': 'POS-0102',
                'from_payment_status': 'unpaid',
                'to_payment_status': 'paid',
                'inventory_policy': INVENTORY_POLICY_DISPATCH_REQUIRED,
            },
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceInventoryService.process_payment_status_changed(msg)
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'deduct_on_paid_disabled')
        mock_publish.assert_not_called()

    @patch('nodeone.core.commerce.inventory.CommerceInventoryService._mark_order_deducted')
    @patch('nodeone.core.commerce.inventory.CommerceInventoryService._order_already_deducted', return_value=False)
    @patch('nodeone.core.commerce.inventory.AuditService.publish_domain_event')
    def test_dispatch_required_deducts_on_delivered(self, mock_publish, _dedup, mock_mark):
        from nodeone.core.commerce.constants import INVENTORY_POLICY_DISPATCH_REQUIRED
        from nodeone.core.commerce.events import COMMERCE_INVENTORY_DEDUCTED
        from nodeone.core.commerce.inventory import CommerceInventoryService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=6,
            organization_id=1,
            event_type='commerce.order.status_changed',
            payload={
                'order_ref': 'POS-0103',
                'from_status': 'ready',
                'to_status': 'delivered',
                'inventory_policy': INVENTORY_POLICY_DISPATCH_REQUIRED,
            },
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceInventoryService.process_order_status_changed(msg)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_INVENTORY_DEDUCTED)
        mock_mark.assert_called_once_with(1, 'POS-0103')

    @patch('nodeone.core.commerce.inventory.AuditService.publish_domain_event')
    def test_retail_skips_deduct_on_delivered(self, mock_publish):
        from nodeone.core.commerce.inventory import CommerceInventoryService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=7,
            organization_id=1,
            event_type='commerce.order.status_changed',
            payload={'order_ref': 'POS-0104', 'from_status': 'ready', 'to_status': 'delivered'},
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceInventoryService.process_order_status_changed(msg)
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'deduct_on_delivered_disabled')
        mock_publish.assert_not_called()

    @patch('nodeone.core.commerce.inventory.AuditService.publish_domain_event')
    def test_skips_second_deduct(self, mock_publish):
        from nodeone.core.commerce.inventory import CommerceInventoryService
        from nodeone.core.platform.events import DomainEventMessage

        with patch(
            'nodeone.core.commerce.inventory.CommerceInventoryService._order_already_deducted',
            return_value=True,
        ):
            msg = DomainEventMessage(
                id=8,
                organization_id=1,
                event_type='commerce.order.payment_status_changed',
                payload={
                    'order_ref': 'POS-0105',
                    'from_payment_status': 'unpaid',
                    'to_payment_status': 'paid',
                },
                source_app_id='eposone',
                created_at=None,
            )
            result = CommerceInventoryService.process_payment_status_changed(msg)
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'already_deducted')
        mock_publish.assert_not_called()

    @patch('nodeone.core.commerce.inventory.CommerceInventoryService.process_order_status_changed')
    def test_handler_swallows_errors(self, mock_process):
        from nodeone.core.commerce.inventory_handlers import _on_order_status_changed
        from nodeone.core.platform.events import DomainEventMessage

        mock_process.side_effect = RuntimeError('boom')
        _on_order_status_changed(
            DomainEventMessage(
                id=3,
                organization_id=1,
                event_type='commerce.order.status_changed',
                payload={'order_ref': 'X', 'to_status': 'confirmed'},
                source_app_id='eposone',
                created_at=None,
            )
        )

    @patch('nodeone.core.commerce.inventory_handlers.subscribe')
    def test_register_handlers_once(self, mock_subscribe):
        import nodeone.core.commerce.inventory_handlers as mod

        mod._REGISTERED = False
        mod.register_commerce_inventory_handlers()
        mod.register_commerce_inventory_handlers()
        self.assertEqual(mock_subscribe.call_count, 2)


class TestCommerceReportService(unittest.TestCase):
    @patch('nodeone.core.commerce.reports.AuditService.publish_domain_event')
    def test_payment_captured_publishes_sale_recorded(self, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_PAYMENT_CAPTURED, COMMERCE_REPORT_SALE_RECORDED
        from nodeone.core.commerce.reports import CommerceReportService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=20,
            organization_id=1,
            event_type=COMMERCE_PAYMENT_CAPTURED,
            payload={
                'order_ref': 'POS-0200',
                'payment_ref': 'PAY-001',
                'amount': 42.5,
                'payment_type': 'cash',
            },
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceReportService.process_payment_captured(msg)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['metric'], 'sale')
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_REPORT_SALE_RECORDED)
        self.assertEqual(mock_publish.call_args[0][2]['amount'], 42.5)

    @patch('nodeone.core.commerce.reports.AuditService.publish_domain_event')
    def test_payment_refunded_publishes_refund_recorded(self, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_REPORT_REFUND_RECORDED
        from nodeone.core.commerce.reports import CommerceReportService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=21,
            organization_id=1,
            event_type='commerce.payment.refunded',
            payload={'order_ref': 'POS-0201', 'payment_ref': 'PAY-002', 'amount': 10},
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceReportService.process_payment_refunded(msg)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_REPORT_REFUND_RECORDED)

    @patch('nodeone.core.commerce.reports.AuditService.publish_domain_event')
    def test_shift_closed_publishes_report_metric(self, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_REPORT_SHIFT_CLOSED
        from nodeone.core.commerce.reports import CommerceReportService
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=22,
            organization_id=1,
            event_type='commerce.cash.shift.closed',
            payload={'register_ref': 'REG-1', 'closing_balance': 500, 'variance': -2.5},
            source_app_id='eposone',
            created_at=None,
        )
        result = CommerceReportService.process_cash_shift_closed(msg)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_REPORT_SHIFT_CLOSED)

    @patch('nodeone.core.commerce.reports.CommerceReportService.process_payment_captured')
    def test_handler_swallows_errors(self, mock_process):
        from nodeone.core.commerce.report_handlers import _on_payment_captured
        from nodeone.core.platform.events import DomainEventMessage

        mock_process.side_effect = RuntimeError('boom')
        _on_payment_captured(
            DomainEventMessage(
                id=23,
                organization_id=1,
                event_type='commerce.payment.captured',
                payload={'order_ref': 'X', 'amount': 1},
                source_app_id='eposone',
                created_at=None,
            )
        )

    @patch('nodeone.core.commerce.report_handlers.subscribe')
    def test_register_handlers_once(self, mock_subscribe):
        import nodeone.core.commerce.report_handlers as mod

        mod._REGISTERED = False
        mod.register_commerce_report_handlers()
        mod.register_commerce_report_handlers()
        self.assertEqual(mock_subscribe.call_count, 4)

    @patch('nodeone.core.commerce.fiscal_handlers.register_commerce_fiscal_handlers')
    @patch('nodeone.core.commerce.inventory_handlers.register_commerce_inventory_handlers')
    @patch('nodeone.core.commerce.stock_handlers.register_commerce_stock_handlers')
    @patch('nodeone.core.commerce.report_handlers.register_commerce_report_handlers')
    def test_register_commerce_bus_handlers(self, mock_report, mock_stock, mock_inventory, mock_fiscal):
        from nodeone.core.commerce.register import register_commerce_bus_handlers

        register_commerce_bus_handlers()
        mock_fiscal.assert_called_once()
        mock_inventory.assert_called_once()
        mock_stock.assert_called_once()
        mock_report.assert_called_once()


class TestStockService(unittest.TestCase):
    @patch('nodeone.core.commerce.stock.CoreStockBalance')
    def test_list_balances(self, mock_model):
        from nodeone.core.commerce.stock import StockService

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.warehouse_org_unit_id = 2
        row.product_ref = 'SKU-1'
        row.quantity_on_hand = 10.0
        row.quantity_reserved = 2.0
        mock_model.query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            row
        ]
        items = StockService.list_balances(1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].quantity_available, 8.0)

    def test_mutate_reserve_insufficient(self):
        from nodeone.core.commerce.constants import STOCK_MOVEMENT_RESERVE
        from nodeone.core.commerce.stock import StockService, StockValidationError

        balance = MagicMock()
        balance.quantity_on_hand = 1.0
        balance.quantity_reserved = 0.0
        with self.assertRaises(StockValidationError):
            StockService._mutate_balance(balance, STOCK_MOVEMENT_RESERVE, 5.0)

    def test_mutate_deduct_releases_reserve(self):
        from nodeone.core.commerce.constants import STOCK_MOVEMENT_DEDUCT
        from nodeone.core.commerce.stock import StockService

        balance = MagicMock()
        balance.quantity_on_hand = 10.0
        balance.quantity_reserved = 3.0
        StockService._mutate_balance(balance, STOCK_MOVEMENT_DEDUCT, 3.0)
        self.assertEqual(balance.quantity_on_hand, 7.0)
        self.assertEqual(balance.quantity_reserved, 0.0)

    @patch('app.db')
    @patch('nodeone.core.commerce.stock.CoreStockMovement')
    @patch('nodeone.core.commerce.stock.StockService._get_or_create_balance')
    @patch('nodeone.core.services.product.ProductService.get_by_ref')
    def test_apply_movement_reserve(self, mock_product, mock_balance_fn, mock_mov, _mock_db):
        from types import SimpleNamespace

        from nodeone.core.commerce.stock import StockService

        mock_product.return_value = SimpleNamespace(status='active', tracks_inventory=True)
        balance = MagicMock()
        balance.quantity_on_hand = 10.0
        balance.quantity_reserved = 0.0
        mock_balance_fn.return_value = balance
        mock_mov.query.filter_by.return_value.first.return_value = None

        result = StockService.apply_movement(
            1,
            warehouse_org_unit_id=2,
            product_ref='SKU-1',
            movement_type='reserve',
            quantity=2,
            idempotency_key='k1',
        )
        self.assertEqual(result['status'], 'applied')
        self.assertEqual(balance.quantity_reserved, 2.0)

    @patch('nodeone.core.commerce.stock_handlers.StockService.apply_order_movement')
    def test_stock_handler_applies_movement(self, mock_apply):
        from nodeone.core.commerce.events import COMMERCE_INVENTORY_RESERVED
        from nodeone.core.commerce.stock_handlers import _on_inventory_movement
        from nodeone.core.platform.events import DomainEventMessage

        msg = DomainEventMessage(
            id=1,
            organization_id=1,
            event_type=COMMERCE_INVENTORY_RESERVED,
            payload={'order_ref': 'POS-1', 'movement': 'reserve'},
            source_app_id='eposone',
            created_at=None,
        )
        _on_inventory_movement(msg)
        mock_apply.assert_called_once_with(1, 'POS-1', 'reserve')

    @patch('nodeone.core.commerce.stock_handlers.subscribe')
    def test_register_stock_handlers_once(self, mock_subscribe):
        import nodeone.core.commerce.stock_handlers as mod

        mod._REGISTERED = False
        mod.register_commerce_stock_handlers()
        mod.register_commerce_stock_handlers()
        self.assertEqual(mock_subscribe.call_count, 4)

    @patch('nodeone.core.commerce.stock.StockService.apply_movement')
    @patch('nodeone.core.commerce.authorization.CommerceAuthorizationService.assert_supervisor', return_value=42)
    def test_record_manual_adjust(self, _mock_supervisor, mock_apply):
        from nodeone.core.commerce.stock import StockService

        mock_apply.return_value = {'status': 'applied'}
        balance = MagicMock()
        balance.id = 1
        balance.organization_id = 1
        balance.warehouse_org_unit_id = 3
        balance.product_ref = 'SKU-1'
        balance.quantity_on_hand = 15.0
        balance.quantity_reserved = 0.0
        with patch.object(StockService, '_resolve_warehouse_org_unit_id', return_value=3):
            with patch('nodeone.core.commerce.stock.CoreStockBalance') as mock_balance_cls:
                mock_balance_cls.query.filter_by.return_value.first.return_value = balance
                dto = StockService.record_manual_adjust(
                    1,
                    {
                        'warehouse_ref': 'WH-01',
                        'product_ref': 'SKU-1',
                        'quantity': 10,
                        'supervisor_user_id': 42,
                    },
                )
        self.assertEqual(dto.quantity_on_hand, 15.0)
        mock_apply.assert_called_once()

    def test_mutate_adjust_negative(self):
        from nodeone.core.commerce.constants import STOCK_MOVEMENT_ADJUST
        from nodeone.core.commerce.stock import StockService, StockValidationError

        balance = MagicMock()
        balance.quantity_on_hand = 5.0
        balance.quantity_reserved = 0.0
        with self.assertRaises(StockValidationError):
            StockService._mutate_balance(balance, STOCK_MOVEMENT_ADJUST, -10.0)
        StockService._mutate_balance(balance, STOCK_MOVEMENT_ADJUST, -3.0)
        self.assertEqual(balance.quantity_on_hand, 2.0)


class TestCashRegisterService(unittest.TestCase):
    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_shift_opened')
    @patch('app.db')
    @patch('nodeone.core.commerce.cash.CoreCashShift')
    def test_open_shift_rejects_duplicate(self, mock_shift_cls, mock_db, _publish):
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.order import OrderValidationError

        mock_shift_cls.query.filter_by.return_value.first.return_value = MagicMock()
        with self.assertRaises(OrderValidationError):
            CashRegisterService.open_shift(1, register_ref='REG-1', opening_balance=50)

    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_shift_reconciling')
    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_count_recorded')
    @patch('nodeone.core.commerce.cash.CashRegisterService.compute_expected_balance', return_value=120.0)
    @patch('app.db')
    @patch('nodeone.core.commerce.cash.CoreCashShift')
    def test_begin_reconcile_hides_variance_from_dto(
        self,
        mock_shift_cls,
        mock_db,
        mock_expected,
        _count,
        _reconciling,
    ):
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.constants import CASH_SHIFT_OPEN, CASH_SHIFT_RECONCILING

        row = MagicMock()
        row.id = 2
        row.organization_id = 1
        row.register_ref = 'REG-1'
        row.status = CASH_SHIFT_OPEN
        row.opening_balance = 100.0
        row.counted_amount = None
        row.expected_balance = None
        row.closing_balance = None
        row.opened_at = None
        row.closed_at = None
        mock_shift_cls.query.filter_by.return_value.first.return_value = row

        dto = CashRegisterService.begin_reconcile(1, 2, counted_amount=115.0)

        self.assertEqual(row.status, CASH_SHIFT_RECONCILING)
        self.assertEqual(row.counted_amount, 115.0)
        self.assertEqual(row.expected_balance, 120.0)
        self.assertIsNone(dto.expected_balance)
        self.assertIsNone(dto.cash_variance)

    @patch('nodeone.core.commerce.cash.CashRegisterService.publish_shift_closed')
    @patch('app.db')
    @patch('nodeone.core.commerce.cash.CoreCashShift')
    def test_close_shift_requires_reconciling(self, mock_shift_cls, mock_db, _publish):
        from nodeone.core.commerce.cash import CashRegisterService
        from nodeone.core.commerce.constants import CASH_SHIFT_OPEN
        from nodeone.core.commerce.order import OrderValidationError

        row = MagicMock()
        row.status = CASH_SHIFT_OPEN
        mock_shift_cls.query.filter_by.return_value.first.return_value = row

        with self.assertRaises(OrderValidationError):
            CashRegisterService.close_shift(1, 2)


class TestCommerceFiscalService(unittest.TestCase):
    @patch('nodeone.core.commerce.fiscal.AuditService.publish_domain_event')
    @patch('nodeone.core.commerce.fiscal.CoreCommercialOrder')
    def test_request_for_pending_order(self, mock_order_cls, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_INVOICE_REQUESTED
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        order = MagicMock()
        order.id = 3
        order.order_ref = 'POS-0003'
        order.fiscal_status = 'pending'
        order.grand_total = 20.0
        order.contact_id = None
        order.payment_status = 'paid'
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = CommerceFiscalService.request_for_order(1, 3)
        self.assertEqual(result['status'], 'queued')
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_INVOICE_REQUESTED)

    @patch('nodeone.core.commerce.fiscal.CoreCommercialOrder')
    def test_process_pending_without_contact_stays_pending(self, mock_order_cls):
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        order = MagicMock()
        order.id = 4
        order.order_ref = 'POS-0004'
        order.fiscal_status = 'pending'
        order.contact_id = None
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        result = CommerceFiscalService.process_pending_order(1, 4)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['reason'], 'no_fiscal_contact')

    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService.process_from_event')
    def test_invoice_requested_handler_swallows_errors(self, mock_process):
        from nodeone.core.commerce.fiscal_handlers import _on_invoice_requested
        from nodeone.core.platform.events import DomainEventMessage

        mock_process.side_effect = RuntimeError('boom')
        msg = DomainEventMessage(
            id=1,
            organization_id=1,
            event_type='commerce.invoice.requested',
            payload={'order_id': 9},
            source_app_id='eposone',
            created_at=None,
        )
        _on_invoice_requested(msg)

    @patch('nodeone.core.commerce.fiscal_handlers.subscribe')
    def test_register_handlers_once(self, mock_subscribe):
        import nodeone.core.commerce.fiscal_handlers as mod

        mod._REGISTERED = False
        mod.register_commerce_fiscal_handlers()
        mod.register_commerce_fiscal_handlers()
        self.assertEqual(mock_subscribe.call_count, 2)

    @patch('nodeone.core.commerce.fiscal.InvoiceService.publish_cancelled')
    @patch('nodeone.core.commerce.fiscal.AuditService.publish_domain_event')
    @patch('nodeone.core.commerce.fiscal.CommerceFiscalService.find_invoice_id_for_order', return_value=77)
    @patch('nodeone.core.commerce.fiscal.CoreCommercialOrder')
    def test_request_credit_note_for_invoiced_order(
        self,
        mock_order_cls,
        mock_find_inv,
        mock_publish,
        mock_cancelled,
    ):
        from nodeone.core.commerce.events import COMMERCE_CREDIT_NOTE_REQUESTED
        from nodeone.core.commerce.fiscal import CommerceFiscalService

        order = MagicMock()
        order.id = 9
        order.order_ref = 'POS-0009'
        order.fiscal_status = 'invoiced'
        mock_order_cls.query.filter_by.return_value.first.return_value = order

        with patch('nodeone.modules.accounting.models.Invoice') as mock_invoice_cls:
            inv = MagicMock()
            inv.number = 'POS-POS-0009'
            mock_invoice_cls.query.filter_by.return_value.first.return_value = inv
            result = CommerceFiscalService.request_credit_note_for_order(1, 9, payment_ref='PAY-9')

        self.assertEqual(result['status'], 'queued')
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][1], COMMERCE_CREDIT_NOTE_REQUESTED)
        mock_cancelled.assert_called_once()


class TestOrderService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_create_requires_lines(self):
        from nodeone.core.commerce.order import OrderService, OrderValidationError

        with self.app.app_context():
            with self.assertRaises(OrderValidationError):
                OrderService.create(1, {})

    @patch('nodeone.core.commerce.order.AuditService.publish_domain_event')
    def test_publish_created(self, mock_publish):
        from nodeone.core.commerce.events import COMMERCE_ORDER_CREATED
        from nodeone.core.commerce.order import OrderService

        OrderService.publish_created(1, order_ref='O-100', status='created', grand_total=9.5)
        mock_publish.assert_called_once()
        args = mock_publish.call_args[0]
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1], COMMERCE_ORDER_CREATED)
        self.assertEqual(args[2]['order_ref'], 'O-100')


class TestInvoiceService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('nodeone.modules.accounting.models.InvoiceLine')
    @patch('nodeone.modules.accounting.models.Invoice')
    def test_get_returns_dto(self, mock_invoice_cls, mock_line_cls):
        from nodeone.core.commerce.invoice import InvoiceService

        row = MagicMock()
        row.id = 10
        row.organization_id = 1
        row.number = 'INV-001'
        row.status = 'posted'
        row.contact_id = 5
        row.currency = 'USD'
        row.grand_total = 100.0
        row.amount_paid = 0.0
        row.date = None

        line = MagicMock()
        line.description = 'Item'
        line.quantity = 1.0
        line.price_unit = 100.0
        line.total = 100.0
        line.product_id = None

        mock_invoice_cls.query.filter_by.return_value.first.return_value = row
        mock_line_cls.query.filter_by.return_value.order_by.return_value.all.return_value = [line]

        dto = InvoiceService.get(1, 10)
        self.assertIsNotNone(dto)
        self.assertEqual(dto.number, 'INV-001')
        self.assertEqual(dto.kind, 'fiscal')
        self.assertEqual(len(dto.lines), 1)


class TestOrderContactRef(unittest.TestCase):
    @staticmethod
    def _contact_dto(**kwargs):
        from nodeone.core.services.contacts import ContactDTO

        defaults = dict(
            id=10,
            organization_id=1,
            display_name='Ana Cliente',
            email='ana@example.com',
            phone=None,
            mobile=None,
            contact_type='person',
            identification_type='consumer_final',
            tax_id=None,
            dv=None,
            is_customer=True,
            is_supplier=False,
            is_member=False,
            is_student=False,
            is_participant=False,
            is_instructor=False,
            is_employee=False,
            active=True,
            roles=('Cliente',),
        )
        defaults.update(kwargs)
        return ContactDTO(**defaults)

    @patch('nodeone.core.services.contacts.ContactService.resolve_ref')
    def test_resolve_order_contact_id_from_ref(self, mock_resolve_ref):
        from nodeone.core.commerce.order import _resolve_order_contact_id

        mock_resolve_ref.return_value = self._contact_dto()
        contact_id = _resolve_order_contact_id(1, {'contact_ref': 'ana@example.com'})
        self.assertEqual(contact_id, 10)
        mock_resolve_ref.assert_called_once_with(1, 'ana@example.com')

    @patch('nodeone.core.services.contacts.ContactService.get')
    def test_resolve_order_contact_id_direct(self, mock_get):
        from nodeone.core.commerce.order import _resolve_order_contact_id

        mock_get.return_value = self._contact_dto(id=7)
        contact_id = _resolve_order_contact_id(1, {'contact_id': 7})
        self.assertEqual(contact_id, 7)

    @patch('nodeone.core.services.contacts.ContactService.get', return_value=None)
    def test_resolve_order_contact_id_invalid(self, _mock_get):
        from nodeone.core.commerce.order import OrderValidationError, _resolve_order_contact_id

        with self.assertRaises(OrderValidationError) as ctx:
            _resolve_order_contact_id(1, {'contact_id': 404})
        self.assertEqual(str(ctx.exception), 'invalid_contact_id')

    @patch('nodeone.core.services.contacts.ContactService.resolve_ref')
    def test_resolve_order_contact_id_inactive_ref(self, mock_resolve_ref):
        from nodeone.core.services.contacts import ContactService
        from nodeone.core.commerce.order import OrderValidationError, _resolve_order_contact_id

        mock_resolve_ref.side_effect = ContactService.ValidationError('contact_inactive')
        with self.assertRaises(OrderValidationError) as ctx:
            _resolve_order_contact_id(1, {'contact_ref': 'legacy:5'})
        self.assertIn('inactive_contact_ref:legacy:5', str(ctx.exception))

    def test_resolve_order_contact_id_optional(self):
        from nodeone.core.commerce.order import _resolve_order_contact_id

        self.assertIsNone(_resolve_order_contact_id(1, {}))


class TestOrderLineProductRef(unittest.TestCase):
    @staticmethod
    def _product(**kwargs):
        from types import SimpleNamespace

        defaults = dict(product_ref='SKU-001', name='Café', status='active', unit_price=3.5)
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    @patch('nodeone.core.services.product.ProductService.get_by_ref')
    def test_build_order_line_resolves_active_product(self, mock_get_by_ref):
        from nodeone.core.commerce.order import _build_order_line

        mock_get_by_ref.return_value = self._product()
        line = _build_order_line(1, {'product_ref': 'SKU-001', 'quantity': 2})
        self.assertEqual(line.description, 'Café')
        self.assertEqual(line.unit_price, 3.5)
        self.assertEqual(line.line_total, 7.0)
        self.assertEqual(line.product_ref, 'SKU-001')
        mock_get_by_ref.assert_called_once_with(1, 'SKU-001')

    @patch('nodeone.core.services.product.ProductService.get_by_ref')
    def test_build_order_line_preserves_explicit_unit_price(self, mock_get_by_ref):
        from nodeone.core.commerce.order import _build_order_line

        mock_get_by_ref.return_value = self._product()
        line = _build_order_line(1, {'product_ref': 'SKU-001', 'unit_price': 4.0, 'quantity': 1})
        self.assertEqual(line.unit_price, 4.0)
        self.assertEqual(line.line_total, 4.0)

    @patch('nodeone.core.services.product.ProductService.get_by_ref', return_value=None)
    def test_build_order_line_invalid_product_ref(self, _mock_get_by_ref):
        from nodeone.core.commerce.order import OrderValidationError, _build_order_line

        with self.assertRaises(OrderValidationError) as ctx:
            _build_order_line(1, {'product_ref': 'MISSING'})
        self.assertIn('invalid_product_ref:MISSING', str(ctx.exception))

    @patch('nodeone.core.services.product.ProductService.get_by_ref')
    def test_build_order_line_inactive_product(self, mock_get_by_ref):
        from nodeone.core.commerce.order import OrderValidationError, _build_order_line

        mock_get_by_ref.return_value = self._product(product_ref='SKU-X', status='archived')
        with self.assertRaises(OrderValidationError) as ctx:
            _build_order_line(1, {'product_ref': 'SKU-X'})
        self.assertIn('invalid_product_ref:SKU-X', str(ctx.exception))

    def test_build_order_line_free_line_without_ref(self):
        from nodeone.core.commerce.order import _build_order_line

        line = _build_order_line(1, {'description': 'Propina', 'unit_price': 1.0, 'quantity': 1})
        self.assertEqual(line.description, 'Propina')
        self.assertEqual(line.unit_price, 1.0)
        self.assertIsNone(line.product_ref)


class TestOrderBranchOrgUnit(unittest.TestCase):
    @patch('nodeone.core.services.org_unit.OrgUnitService.get_by_ref')
    def test_resolve_branch_ref(self, mock_get_by_ref):
        from nodeone.core.commerce.order import _resolve_branch_org_unit_id

        mock_get_by_ref.return_value = MagicMock(id=12, unit_type='branch')
        branch_id = _resolve_branch_org_unit_id(1, {'branch_ref': 'SUC-01'})
        self.assertEqual(branch_id, 12)

    @patch('nodeone.core.services.org_unit.OrgUnitService.list_units')
    def test_resolve_branch_org_unit_id(self, mock_list):
        from nodeone.core.commerce.order import OrderValidationError, _resolve_branch_org_unit_id

        mock_list.return_value = [MagicMock(id=3, unit_type='branch')]
        self.assertEqual(_resolve_branch_org_unit_id(1, {'branch_org_unit_id': 3}), 3)
        with self.assertRaises(OrderValidationError):
            _resolve_branch_org_unit_id(1, {'branch_org_unit_id': 99})


class TestOrderSplitBill(unittest.TestCase):
    @patch('nodeone.core.services.product.ProductService.get_by_ref')
    @patch('nodeone.core.commerce.order.OrderService.publish_created')
    @patch('nodeone.core.commerce.order.OrderService._next_order_ref', return_value='POS-0009')
    @patch('app.db')
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_split_moves_lines_to_child(self, mock_order_cls, mock_db, _mock_ref, _mock_publish, mock_get_product):
        from nodeone.core.commerce.order import OrderService

        mock_get_product.return_value = SimpleNamespace(
            product_ref='SKU-1',
            name='Agua',
            status='active',
            unit_price=1.0,
        )
        line_a = MagicMock()
        line_a.description = 'Café'
        line_a.quantity = 1.0
        line_a.unit_price = 3.0
        line_a.line_total = 3.0
        line_a.product_ref = None
        line_a.line_status = 'pending'
        line_b = MagicMock()
        line_b.description = 'Agua'
        line_b.quantity = 2.0
        line_b.unit_price = 1.0
        line_b.line_total = 2.0
        line_b.product_ref = 'SKU-1'
        line_b.line_status = 'pending'

        parent = MagicMock()
        parent.id = 5
        parent.organization_id = 1
        parent.payment_status = 'unpaid'
        parent.contact_id = 10
        parent.branch_org_unit_id = 2
        parent.currency = 'USD'
        parent.tax_total = 0.0
        parent.version = 1
        parent.lines = [line_a, line_b]
        parent.operational_status = 'draft'

        mock_order_cls.query.filter_by.return_value.first.return_value = parent
        child = MagicMock()
        child.id = 99
        child.organization_id = 1
        child.order_ref = 'POS-0009'
        child.operational_status = 'draft'
        child.payment_status = 'unpaid'
        child.fiscal_status = 'not_required'
        child.contact_id = 10
        child.branch_org_unit_id = 2
        child.parent_order_id = 5
        child.currency = 'USD'
        child.subtotal = 2.0
        child.tax_total = 0.0
        child.grand_total = 2.0
        child.amount_paid = 0.0
        child.source_app_id = 'eposone'
        child.created_at = None
        child.lines = [line_b]
        mock_order_cls.return_value = child

        dto = OrderService.split_order(1, 5, [1])
        self.assertEqual(dto.parent_order_id, 5)
        mock_db.session.delete.assert_called_with(line_b)
        mock_db.session.commit.assert_called_once()


class TestOrderTransfer(unittest.TestCase):
    @patch('nodeone.core.commerce.order.OrderService.publish_transferred')
    @patch('app.db')
    @patch('nodeone.core.commerce.pos.PosTerminalService.get')
    @patch('nodeone.core.commerce.pos.PosTerminalService.resolve_id', return_value=7)
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_transfer_updates_terminal(
        self,
        mock_order_cls,
        mock_resolve,
        mock_terminal_get,
        mock_db,
        mock_publish,
    ):
        from nodeone.core.commerce.dtos import PosTerminalDTO
        from nodeone.core.commerce.order import OrderService

        row = MagicMock()
        row.id = 5
        row.organization_id = 1
        row.order_ref = 'POS-0001'
        row.payment_status = 'unpaid'
        row.operational_status = 'ready'
        row.pos_terminal_id = 3
        row.version = 2
        row.contact_id = None
        row.branch_org_unit_id = None
        row.parent_order_id = None
        row.currency = 'USD'
        row.fiscal_status = 'not_required'
        row.subtotal = 10.0
        row.tax_total = 0.0
        row.grand_total = 10.0
        row.amount_paid = 0.0
        row.source_app_id = 'eposone'
        row.created_at = None
        row.lines = []
        mock_order_cls.query.filter_by.return_value.first.return_value = row
        mock_terminal_get.return_value = PosTerminalDTO(
            id=7,
            organization_id=1,
            terminal_ref='CAJA-01',
            register_ref='REG-1',
            status='active',
            device_label=None,
        )

        dto = OrderService.transfer_to_terminal(1, 5, {'terminal_ref': 'CAJA-01'})
        self.assertEqual(dto.pos_terminal_id, 7)
        self.assertEqual(row.pos_terminal_id, 7)
        mock_publish.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @patch('nodeone.core.commerce.pos.PosTerminalService.resolve_id', return_value=7)
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_transfer_rejects_paid_order(self, mock_order_cls, _mock_resolve):
        from nodeone.core.commerce.order import OrderService, OrderValidationError

        row = MagicMock()
        row.payment_status = 'paid'
        row.operational_status = 'delivered'
        mock_order_cls.query.filter_by.return_value.first.return_value = row

        with self.assertRaises(OrderValidationError) as ctx:
            OrderService.transfer_to_terminal(1, 5, {'terminal_id': 7})
        self.assertEqual(str(ctx.exception), 'order_already_paid')


class TestPosTerminalResolve(unittest.TestCase):
    @patch('nodeone.core.commerce.pos.CorePosTerminal')
    def test_resolve_by_ref(self, mock_cls):
        from nodeone.core.commerce.pos import PosTerminalService

        mock_cls.query.filter_by.return_value.first.return_value = MagicMock(id=11)
        terminal_id = PosTerminalService.resolve_id(1, {'terminal_ref': 'HH-01'})
        self.assertEqual(terminal_id, 11)


if __name__ == '__main__':
    unittest.main()
