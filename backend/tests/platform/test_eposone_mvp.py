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


if __name__ == '__main__':
    unittest.main()
