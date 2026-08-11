"""P0.1 — Cash Shift HTTP v1 (Device Bearer): auth, open, idempotencia, arqueo, close."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _device(*, oid=1, register_ref='REG-MF-1'):
    return SimpleNamespace(organization_id=oid, register_ref=register_ref, status='active')


def _shift_row(
    *,
    shift_id=10,
    oid=1,
    register_ref='REG-MF-1',
    status='open',
    opening=100.0,
    client_shift_id='cs-1',
    cashier_contact_id=7,
    cashier_name='Ana',
    counted=None,
    expected=None,
    closing=None,
    opened_at=None,
    closed_at=None,
    closed_by=None,
):
    row = MagicMock()
    row.id = shift_id
    row.organization_id = oid
    row.register_ref = register_ref
    row.status = status
    row.opening_balance = opening
    row.client_shift_id = client_shift_id
    row.cashier_contact_id = cashier_contact_id
    row.cashier_name = cashier_name
    row.counted_amount = counted
    row.expected_balance = expected
    row.closing_balance = closing
    row.opened_at = opened_at
    row.closed_at = closed_at
    row.closed_by_cashier_contact_id = closed_by
    return row


class TestCashShiftHttpBlueprint(unittest.TestCase):
    def test_blueprint_prefix(self):
        # Importar app primero: si se importa cash_shifts_v1_routes antes,
        # el registro de eposone falla por import circular y /api/v1/cash* queda 404.
        from app import app as flask_app

        self.assertIn('eposone_cash_v1', flask_app.blueprints)
        bp = flask_app.blueprints['eposone_cash_v1']
        self.assertEqual(bp.url_prefix, '/api/v1/cash')


class TestCashShiftHttpAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()
        assert 'eposone_cash_v1' in flask_app.blueprints

    def test_current_requires_auth(self):
        r = self.client.get('/api/v1/cash/shifts/current')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json().get('error'), 'unauthorized')

    def test_open_requires_auth(self):
        r = self.client.post(
            '/api/v1/cash/shifts',
            json={'cashier_contact_id': 7, 'opening_float': 50},
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json().get('error'), 'unauthorized')

    def test_close_requires_auth(self):
        r = self.client.post(
            '/api/v1/cash/shifts/10/close',
            json={'cashier_contact_id': 7, 'counted_amount': 50},
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json().get('error'), 'unauthorized')


class TestCashShiftHttpOpenIdempotency(unittest.TestCase):
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreOrgUnit')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashRegisterService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashierService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreCashShift')
    def test_open_new_client_shift_id_created(
        self, mock_shift_cls, mock_cashier_svc, mock_reg_svc, mock_unit_cls
    ):
        from nodeone.modules.eposone.cash_shift_http_service import CashShiftHttpService

        mock_shift_cls.query.filter_by.return_value.first.return_value = None
        mock_cashier_svc.require_cashier.return_value = SimpleNamespace(
            id=7, display_name='Ana'
        )
        mock_reg_svc.open_shift.return_value = SimpleNamespace(id=42)
        created_row = _shift_row(shift_id=42, client_shift_id='uuid-new')
        # After open: fetch by id
        mock_shift_cls.query.filter_by.side_effect = [
            MagicMock(first=MagicMock(return_value=None)),  # client_shift_id lookup
            MagicMock(first=MagicMock(return_value=created_row)),  # by id
        ]
        mock_unit_cls.query.filter_by.return_value.first.return_value = SimpleNamespace(
            name='Caja 1'
        )
        mock_reg_svc.compute_expected_balance.return_value = 100.0

        data, created = CashShiftHttpService.open_shift(
            _device(),
            {
                'client_shift_id': 'uuid-new',
                'cashier_contact_id': 7,
                'opening_float': 100,
            },
        )
        self.assertTrue(created)
        self.assertEqual(data['shift_id'], 42)
        self.assertEqual(data['client_shift_id'], 'uuid-new')
        mock_reg_svc.open_shift.assert_called_once()

    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreOrgUnit')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashRegisterService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreCashShift')
    def test_open_idempotent_same_client_shift_id(
        self, mock_shift_cls, mock_reg_svc, mock_unit_cls
    ):
        from nodeone.modules.eposone.cash_shift_http_service import CashShiftHttpService

        existing = _shift_row(shift_id=42, client_shift_id='uuid-same')
        mock_shift_cls.query.filter_by.return_value.first.return_value = existing
        mock_unit_cls.query.filter_by.return_value.first.return_value = SimpleNamespace(
            name='Caja 1'
        )
        mock_reg_svc.compute_expected_balance.return_value = 100.0

        data, created = CashShiftHttpService.open_shift(
            _device(),
            {
                'client_shift_id': 'uuid-same',
                'cashier_contact_id': 7,
                'opening_float': 100,
            },
        )
        self.assertFalse(created)
        self.assertEqual(data['shift_id'], 42)
        mock_reg_svc.open_shift.assert_not_called()

    @patch('nodeone.modules.eposone.cash_shift_http_service.CashierService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashRegisterService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreCashShift')
    def test_open_conflict_shift_already_open(
        self, mock_shift_cls, mock_reg_svc, mock_cashier_svc
    ):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.modules.eposone.cash_shift_http_service import (
            CashShiftHttpError,
            CashShiftHttpService,
        )

        mock_shift_cls.query.filter_by.return_value.first.return_value = None
        mock_cashier_svc.require_cashier.return_value = SimpleNamespace(
            id=7, display_name='Ana'
        )
        mock_reg_svc.open_shift.side_effect = OrderValidationError('shift_already_open')

        with self.assertRaises(CashShiftHttpError) as ctx:
            CashShiftHttpService.open_shift(
                _device(),
                {
                    'client_shift_id': 'uuid-other',
                    'cashier_contact_id': 7,
                    'opening_float': 50,
                },
            )
        self.assertEqual(ctx.exception.code, 'shift_already_open')
        self.assertEqual(ctx.exception.http_status, 409)


class TestCashShiftHttpIdempotencyHeader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()
        assert 'eposone_cash_v1' in flask_app.blueprints

    @patch('nodeone.modules.eposone.cash_shift_http_service.CashShiftHttpService.open_shift')
    @patch(
        'nodeone.modules.eposone.cash_shifts_v1_routes.DeviceProvisioningService.authenticate_bearer'
    )
    def test_idempotency_key_header_maps_to_client_shift_id(self, mock_auth, mock_open):
        mock_auth.return_value = _device()
        mock_open.return_value = (
            {
                'shift_id': 5,
                'client_shift_id': 'hdr-key-1',
                'status': 'open',
            },
            True,
        )
        r = self.client.post(
            '/api/v1/cash/shifts',
            json={'cashier_contact_id': 7, 'opening_float': 20},
            headers={
                'Authorization': 'Bearer tok',
                'Idempotency-Key': 'hdr-key-1',
            },
        )
        self.assertEqual(r.status_code, 201)
        body = mock_open.call_args[0][1]
        self.assertEqual(body.get('client_shift_id'), 'hdr-key-1')


class TestCashShiftHttpCurrentExpected(unittest.TestCase):
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreOrgUnit')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashRegisterService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreCashShift')
    def test_get_current_includes_expected_when_open(
        self, mock_shift_cls, mock_reg_svc, mock_unit_cls
    ):
        from nodeone.modules.eposone.cash_shift_http_service import CashShiftHttpService

        row = _shift_row(status='open', expected=None)
        q = MagicMock()
        q.filter.return_value.order_by.return_value.first.return_value = row
        mock_shift_cls.query.filter_by.return_value = q
        mock_unit_cls.query.filter_by.return_value.first.return_value = SimpleNamespace(
            name='Caja 1'
        )
        mock_reg_svc.compute_expected_balance.return_value = 175.5

        data = CashShiftHttpService.get_current(_device())
        self.assertIsNotNone(data)
        self.assertEqual(data['expected_balance'], 175.5)
        mock_reg_svc.compute_expected_balance.assert_called_once_with(10)


class TestCashExpectedFormula(unittest.TestCase):
    def test_cash_expected_opening_plus_sales_in_minus_out_refunds(self):
        from nodeone.modules.eposone import shift_close_service as scs

        shift = SimpleNamespace(
            id=1,
            opening_balance=100.0,
            opened_at=None,
            closed_at=None,
        )
        with (
            patch.object(
                scs,
                '_movement_breakdown',
                return_value={
                    'sale_cash': 10.0,
                    'cash_in': 5.0,
                    'cash_out': 3.0,
                    'refund_cash': 2.0,
                },
            ),
            patch.object(scs, '_od_payments_for_shift', return_value=[]),
        ):
            out = scs.cash_expected_for_shift(shift, include_opening=True)
        # 100 + (10+0) + 5 - 3 - (2+0) = 110
        self.assertEqual(out['opening'], 100.0)
        self.assertEqual(out['cash_sales'], 10.0)
        self.assertEqual(out['cash_in'], 5.0)
        self.assertEqual(out['cash_out'], 3.0)
        self.assertEqual(out['refunds'], 2.0)
        self.assertEqual(out['expected'], 110.0)

    def test_cash_expected_adds_od_cash_payments_only(self):
        from nodeone.modules.eposone import shift_close_service as scs

        shift = SimpleNamespace(
            id=1,
            opening_balance=50.0,
            opened_at=None,
            closed_at=None,
        )
        cash_pay = SimpleNamespace(method='cash', amount=20.0, kind='payment')
        card_pay = SimpleNamespace(method='visa', amount=30.0, kind='payment')
        refund = SimpleNamespace(method='efectivo', amount=4.0, kind='refund')
        with (
            patch.object(
                scs,
                '_movement_breakdown',
                return_value={
                    'sale_cash': 0.0,
                    'cash_in': 0.0,
                    'cash_out': 0.0,
                    'refund_cash': 0.0,
                },
            ),
            patch.object(
                scs,
                '_od_payments_for_shift',
                return_value=[
                    (cash_pay, MagicMock()),
                    (card_pay, MagicMock()),
                    (refund, MagicMock()),
                ],
            ),
        ):
            out = scs.cash_expected_for_shift(shift, include_opening=True)
        # 50 + 20 + 0 - 0 - 4 = 66 (visa ignored)
        self.assertEqual(out['cash_sales'], 20.0)
        self.assertEqual(out['refunds'], 4.0)
        self.assertEqual(out['expected'], 66.0)


class TestCashShiftHttpClose(unittest.TestCase):
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreOrgUnit')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashRegisterService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashierService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreCashShift')
    def test_close_one_shot_persists_variance(
        self, mock_shift_cls, mock_cashier_svc, mock_reg_svc, mock_unit_cls
    ):
        from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED, CASH_SHIFT_OPEN
        from nodeone.modules.eposone.cash_shift_http_service import CashShiftHttpService

        open_row = _shift_row(shift_id=10, status=CASH_SHIFT_OPEN)
        closed_row = _shift_row(
            shift_id=10,
            status=CASH_SHIFT_CLOSED,
            counted=115.0,
            expected=120.0,
            closing=115.0,
            closed_by=7,
        )
        mock_shift_cls.query.filter_by.return_value.first.side_effect = [
            open_row,
            closed_row,
        ]
        mock_cashier_svc.require_cashier.return_value = SimpleNamespace(
            id=7, display_name='Ana'
        )
        mock_unit_cls.query.filter_by.return_value.first.return_value = SimpleNamespace(
            name='Caja 1'
        )

        data = CashShiftHttpService.close_shift(
            _device(),
            10,
            {'cashier_contact_id': 7, 'counted_amount': 115},
        )
        mock_reg_svc.close_shift_counted.assert_called_once()
        kwargs = mock_reg_svc.close_shift_counted.call_args.kwargs
        self.assertEqual(kwargs['counted_amount'], 115.0)
        self.assertEqual(kwargs['cashier_contact_id'], 7)
        self.assertEqual(data['status'], CASH_SHIFT_CLOSED)
        self.assertEqual(data['counted_amount'], 115.0)
        self.assertEqual(data['expected_balance'], 120.0)
        self.assertEqual(data['cash_variance'], -5.0)

    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreOrgUnit')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CashRegisterService')
    @patch('nodeone.modules.eposone.cash_shift_http_service.CoreCashShift')
    def test_close_replay_already_closed_idempotent(
        self, mock_shift_cls, mock_reg_svc, mock_unit_cls
    ):
        from nodeone.core.commerce.constants import CASH_SHIFT_CLOSED
        from nodeone.modules.eposone.cash_shift_http_service import CashShiftHttpService

        closed_row = _shift_row(
            shift_id=10,
            status=CASH_SHIFT_CLOSED,
            counted=100.0,
            expected=100.0,
            closing=100.0,
        )
        mock_shift_cls.query.filter_by.return_value.first.return_value = closed_row
        mock_unit_cls.query.filter_by.return_value.first.return_value = SimpleNamespace(
            name='Caja 1'
        )

        data = CashShiftHttpService.close_shift(
            _device(),
            10,
            {'cashier_contact_id': 7, 'counted_amount': 999},
        )
        mock_reg_svc.close_shift_counted.assert_not_called()
        self.assertEqual(data['status'], CASH_SHIFT_CLOSED)
        self.assertEqual(data['counted_amount'], 100.0)
        self.assertEqual(data['cash_variance'], 0.0)


if __name__ == '__main__':
    unittest.main()
