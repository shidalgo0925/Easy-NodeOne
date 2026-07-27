"""Resolución de métodos de pago Order Domain (Yappy, alias, referencia)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from nodeone.modules.eposone.order_payment_service import (
    METHOD_ALIASES,
    OrderPaymentService,
    _fold,
)


class TestPaymentMethodAliases(unittest.TestCase):
    def test_fold_strips_accents_and_spaces(self):
        self.assertEqual(_fold('Crédito Cliente'), 'credito_cliente')
        self.assertEqual(_fold('Yappy'), 'yappy')
        self.assertEqual(_fold('Gift Card'), 'gift_card')

    def test_aliases_cover_apk_forms(self):
        for raw, expected in (
            ('efectivo', 'cash'),
            ('Yappy', 'yappy'),
            ('tarjeta', 'card'),
            ('vale', 'voucher'),
            ('giftcard', 'gift_card'),
            ('master_card', 'mastercard'),
        ):
            self.assertEqual(METHOD_ALIASES[_fold(raw)], expected)

    def test_ensure_reference_autofills_when_required(self):
        method = SimpleNamespace(requires_reference=True)
        ref = OrderPaymentService._ensure_reference(
            method,
            reference=None,
            authorization_code=None,
            payment_ref='pay-abc',
        )
        self.assertEqual(ref, 'NR-pay-abc')

    def test_ensure_reference_keeps_explicit(self):
        method = SimpleNamespace(requires_reference=True)
        ref = OrderPaymentService._ensure_reference(
            method,
            reference='  TX-99  ',
            authorization_code=None,
            payment_ref='pay-abc',
        )
        self.assertEqual(ref, 'TX-99')

    @patch.object(OrderPaymentService, 'ensure_methods_for_org')
    def test_resolve_method_by_label(self, mock_ensure):
        yappy = SimpleNamespace(id=5, method_key='yappy', label='Yappy', enabled=True)
        mock_ensure.return_value = [yappy]
        with patch(
            'nodeone.modules.eposone.order_payment_service.EposonePaymentMethod'
        ) as mock_cls:
            mock_cls.query = MagicMock()
            row, key = OrderPaymentService._resolve_method(5, {'method': 'Yappy'})
        self.assertEqual(key, 'yappy')
        self.assertIs(row, yappy)

    @patch.object(OrderPaymentService, 'ensure_methods_for_org')
    def test_resolve_method_card_alias(self, mock_ensure):
        card = SimpleNamespace(id=11, method_key='card', label='Tarjeta', enabled=True)
        mock_ensure.return_value = [card]
        row, key = OrderPaymentService._resolve_method(5, {'payment_type': 'card'})
        self.assertEqual(key, 'card')
        self.assertIs(row, card)

    def test_sync_tip_inferred_from_payment_amount(self):
        order = SimpleNamespace(
            subtotal=12.84,
            tax=0.0,
            discount=0.0,
            tip=0.0,
            total=12.84,
            amount_paid=0.0,
        )
        OrderPaymentService._sync_tip_before_payment(order, {}, 14.12)
        self.assertAlmostEqual(order.tip, 1.28, places=2)
        self.assertAlmostEqual(order.total, 14.12, places=2)

    def test_sync_tip_explicit_propina(self):
        order = SimpleNamespace(
            subtotal=18.73,
            tax=0.0,
            discount=0.0,
            tip=0.0,
            total=18.73,
            amount_paid=0.0,
        )
        OrderPaymentService._sync_tip_before_payment(order, {'propina': 2.81}, 21.54)
        self.assertAlmostEqual(order.tip, 2.81, places=2)
        self.assertAlmostEqual(order.total, 21.54, places=2)

    def test_sync_tip_does_not_accumulate_when_tip_already_set(self):
        order = SimpleNamespace(
            subtotal=13.38,
            tax=0.0,
            discount=0.0,
            tip=1.34,
            total=14.72,
            amount_paid=0.0,
        )
        OrderPaymentService._sync_tip_before_payment(order, {}, 14.72)
        self.assertAlmostEqual(order.tip, 1.34, places=2)
        self.assertAlmostEqual(order.total, 14.72, places=2)


class TestFinancialStateCents(unittest.TestCase):
    def test_partial_clears_when_paid_covers_rounded_total(self):
        from nodeone.modules.eposone.order_domain import apply_financial_state

        order = SimpleNamespace(
            total=17.1735,
            amount_paid=17.17,
            tip=0.0,
            payment_status='partial',
            financially_closed=False,
            status='open',
        )
        apply_financial_state(order)
        self.assertEqual(order.payment_status, 'paid')
        self.assertTrue(order.financially_closed)
        self.assertEqual(order.status, 'closed')
        self.assertAlmostEqual(order.total, 17.17, places=2)
        self.assertAlmostEqual(order.amount_paid, 17.17, places=2)


if __name__ == '__main__':
    unittest.main()
