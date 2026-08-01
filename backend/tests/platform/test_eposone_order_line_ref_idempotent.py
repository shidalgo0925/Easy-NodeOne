"""Order Domain — no duplicar line_ref en producto.agregado."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _device():
    return SimpleNamespace(
        organization_id=9,
        terminal_ref='dev-1',
        pos_ref='ptv-01',
        register_ref='CAJA_01',
        branch_ref=None,
    )


class TestProductoAgregadoLineRefIdempotent(unittest.TestCase):
    @patch('nodeone.modules.eposone.order_domain.OrderDomainService._append_event')
    @patch('nodeone.modules.eposone.order_domain.OrderDomainService._require_owner')
    @patch('nodeone.modules.eposone.order_domain.EposoneOrderEvent')
    @patch('nodeone.modules.eposone.order_domain.EposoneOrderItem')
    @patch('nodeone.modules.eposone.order_domain.OrderDomainService.get_order')
    @patch('app.db')
    def test_second_event_same_line_ref_does_not_insert(
        self,
        mock_db,
        mock_get,
        mock_item_cls,
        mock_event_cls,
        _owner,
        mock_append,
    ):
        from nodeone.modules.eposone.order_domain import OrderDomainService

        order = MagicMock()
        order.id = 106
        order.organization_id = 9
        order.user_ref = 'Cajero1'
        mock_get.return_value = order
        mock_event_cls.query.filter_by.return_value.first.return_value = None
        mock_item_cls.query.filter_by.return_value.filter.return_value.first.return_value = (
            MagicMock()
        )

        OrderDomainService.apply_event(
            _device(),
            106,
            {
                'type': 'producto.agregado',
                'event_id': 'evt-dup-l2',
                'payload': {
                    'line_ref': 'L2',
                    'product_ref': 'bandeja_de_10_tacos',
                    'qty': 1,
                    'unit_price': 22.99,
                    'tax': 1.5,
                },
            },
        )

        mock_item_cls.assert_not_called()
        mock_append.assert_called_once()
        mock_db.session.begin_nested.assert_not_called()
        mock_db.session.execute.assert_called_once()


class TestProductoAgregadoInsertsWhenAbsent(unittest.TestCase):
    @patch('nodeone.modules.eposone.order_domain._recalc')
    @patch('nodeone.modules.eposone.order_domain.OrderDomainService._append_event')
    @patch('nodeone.modules.eposone.order_domain.OrderDomainService._require_owner')
    @patch('nodeone.modules.eposone.order_domain.EposoneOrderEvent')
    @patch('nodeone.modules.eposone.order_domain.EposoneOrderItem')
    @patch('nodeone.modules.eposone.order_domain.OrderDomainService.get_order')
    @patch('app.db')
    def test_inserts_when_line_ref_absent(
        self,
        mock_db,
        mock_get,
        mock_item_cls,
        mock_event_cls,
        _owner,
        mock_append,
        mock_recalc,
    ):
        from nodeone.modules.eposone.order_domain import OrderDomainService

        order = MagicMock()
        order.id = 200
        order.organization_id = 9
        order.user_ref = 'Cajero1'
        order.items = MagicMock()
        mock_get.return_value = order
        mock_event_cls.query.filter_by.return_value.first.return_value = None
        mock_item_cls.query.filter_by.return_value.filter.return_value.first.return_value = None
        nested = MagicMock()
        mock_db.session.begin_nested.return_value = nested
        nested.__enter__ = MagicMock(return_value=nested)
        nested.__exit__ = MagicMock(return_value=False)

        OrderDomainService.apply_event(
            _device(),
            200,
            {
                'type': 'producto.agregado',
                'event_id': 'evt-new-l1',
                'payload': {
                    'line_ref': 'L1',
                    'product_ref': 'quesabirrias',
                    'qty': 1,
                    'unit_price': 24.99,
                    'tax': 1.6,
                },
            },
        )

        mock_item_cls.assert_called_once()
        order.items.append.assert_called_once()
        mock_recalc.assert_called_once_with(order)
        mock_append.assert_called_once()
        mock_db.session.begin_nested.assert_called()
        mock_db.session.execute.assert_called_once()


if __name__ == '__main__':
    unittest.main()
