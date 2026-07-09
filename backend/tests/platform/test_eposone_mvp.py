"""Tests EPosOne MVP — Etapa 14."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestOrderServiceMVP(unittest.TestCase):
    def test_next_order_ref_sequence(self):
        from nodeone.core.commerce.order import OrderService

        with patch('nodeone.core.commerce.order.CoreCommercialOrder') as mock_model:
            mock_model.query.filter_by.return_value.with_entities.return_value.all.return_value = [
                ('POS-0003',),
                ('POS-0001',),
            ]
            ref = OrderService._next_order_ref(1)
        self.assertEqual(ref, 'POS-0004')

    @patch('nodeone.core.commerce.order.AuditService.publish_domain_event')
    @patch('app.db')
    @patch('nodeone.core.commerce.order.CoreCommercialOrder')
    def test_create_order(self, mock_order_cls, mock_db, mock_publish):
        from nodeone.core.commerce.order import OrderService

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.order_ref = 'POS-0001'
        row.status = 'draft'
        row.contact_id = None
        row.currency = 'USD'
        row.subtotal = 10.0
        row.tax_total = 0.0
        row.grand_total = 10.0
        row.source_app_id = 'eposone'
        row.created_at = None
        row.lines = [
            MagicMock(
                description='Café',
                quantity=1.0,
                unit_price=10.0,
                line_total=10.0,
                product_ref=None,
            )
        ]

        def _add(r):
            r.lines = row.lines

        mock_db.session.add.side_effect = _add
        mock_order_cls.return_value = row

        with patch.object(OrderService, '_next_order_ref', return_value='POS-0001'):
            dto = OrderService.create(
                1,
                {'lines': [{'description': 'Café', 'quantity': 1, 'unit_price': 10}]},
            )
        self.assertEqual(dto.order_ref, 'POS-0001')
        self.assertEqual(dto.grand_total, 10.0)
        mock_publish.assert_called_once()


class TestEPosOneAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_orders_api_requires_auth(self):
        with self.app.test_client() as c:
            r = c.get('/api/eposone/orders')
            self.assertIn(r.status_code, (302, 401))

    def test_branches_api_requires_auth(self):
        with self.app.test_client() as c:
            r = c.get('/api/eposone/branches')
            self.assertIn(r.status_code, (302, 401))

    def test_warehouses_api_requires_auth(self):
        with self.app.test_client() as c:
            r = c.get('/api/eposone/warehouses')
            self.assertIn(r.status_code, (302, 401))

    def test_registers_api_requires_auth(self):
        with self.app.test_client() as c:
            r = c.get('/api/eposone/registers')
            self.assertIn(r.status_code, (302, 401))

    def test_orders_fiscal_api_requires_auth(self):
        with self.app.test_client() as c:
            r = c.post('/api/eposone/orders/1/fiscal')
            self.assertIn(r.status_code, (302, 401))

    @patch('nodeone.core.commerce.pos.CorePosTerminal')
    def test_list_terminals(self, mock_model):
        from nodeone.core.commerce.pos import PosTerminalService

        row = MagicMock()
        row.id = 1
        row.organization_id = 1
        row.terminal_ref = 'TAB-01'
        row.register_ref = 'REG-1'
        row.status = 'active'
        row.device_label = 'Tablet mostrador'
        mock_model.query.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [row]
        items = PosTerminalService.list_terminals(1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].terminal_ref, 'TAB-01')


class TestEPosOneSyncHandler(unittest.TestCase):
    def test_unsupported_operation(self):
        from nodeone.core.commerce.order import OrderValidationError
        from nodeone.core.sync.queue import SyncOperationDTO
        from nodeone.modules.eposone.sync_handlers import apply_eposone_sync_operation

        dto = SyncOperationDTO(
            id=1,
            organization_id=1,
            client_id='t1',
            idempotency_key='k',
            operation_type='unknown',
            status='pending',
            entity_type=None,
            entity_ref=None,
            payload={},
            base_version=None,
            retry_count=0,
            conflict_reason=None,
            created_at=None,
            applied_at=None,
        )
        with self.assertRaises(OrderValidationError):
            apply_eposone_sync_operation(dto)

    @patch('nodeone.modules.eposone.sync_handlers.OrderService.transition_status')
    def test_transition_order_status_operation(self, mock_transition):
        from nodeone.core.sync.queue import SyncOperationDTO
        from nodeone.modules.eposone.sync_handlers import apply_eposone_sync_operation

        dto = SyncOperationDTO(
            id=2,
            organization_id=1,
            client_id='t1',
            idempotency_key='k2',
            operation_type='transition_order_status',
            status='pending',
            entity_type='order',
            entity_ref='POS-0001',
            payload={'order_id': 5, 'status': 'confirmed'},
            base_version=1,
            retry_count=0,
            conflict_reason=None,
            created_at=None,
            applied_at=None,
        )
        apply_eposone_sync_operation(dto)
        mock_transition.assert_called_once_with(
            1,
            5,
            'confirmed',
            source_app_id='eposone',
            reason=None,
        )

    @patch('nodeone.core.commerce.cash.CashRegisterService.record_manual_movement')
    def test_manual_cash_movement_operation(self, mock_manual):
        from nodeone.core.sync.queue import SyncOperationDTO
        from nodeone.modules.eposone.sync_handlers import apply_eposone_sync_operation

        dto = SyncOperationDTO(
            id=3,
            organization_id=1,
            client_id='t1',
            idempotency_key='k3',
            operation_type='manual_cash_movement',
            status='pending',
            entity_type='cash_shift',
            entity_ref='REG-1',
            payload={
                'shift_id': 9,
                'movement_type': 'cash_in',
                'amount': 50,
                'supervisor_user_id': 42,
            },
            base_version=None,
            retry_count=0,
            conflict_reason=None,
            created_at=None,
            applied_at=None,
        )
        apply_eposone_sync_operation(dto)
        mock_manual.assert_called_once()
        self.assertEqual(mock_manual.call_args[0][1], 9)
        self.assertEqual(mock_manual.call_args[0][2], 'cash_in')

    def test_supported_operations_catalog(self):
        from nodeone.modules.eposone.sync_handlers import EPOSONE_SYNC_OPERATIONS

        self.assertIn('refund_payment', EPOSONE_SYNC_OPERATIONS)
        self.assertIn('manual_cash_movement', EPOSONE_SYNC_OPERATIONS)


class TestPlatformSyncAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_sync_process_requires_auth(self):
        with self.app.test_client() as c:
            r = c.post('/api/platform/sync/operations/process')
            self.assertIn(r.status_code, (302, 401))


if __name__ == '__main__':
    unittest.main()
