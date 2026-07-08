"""Tests bus de eventos — Etapa 8."""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _fake_row(
    *,
    event_id: int = 1,
    organization_id: int = 1,
    event_type: str = 'eposone.order.created',
    source_app_id: str = 'eposone',
    payload: dict | None = None,
    status: str = 'pending',
):
    return SimpleNamespace(
        id=event_id,
        organization_id=organization_id,
        event_type=event_type,
        source_app_id=source_app_id,
        payload=payload or {},
        status=status,
        error_message=None,
        created_at=datetime.utcnow(),
        dispatched_at=None,
    )


class TestEventBusHandlers(unittest.TestCase):
    def setUp(self):
        from nodeone.core.platform.events import clear_subscribers

        clear_subscribers()
        os.environ['NODEONE_EVENT_BUS_SYNC'] = '0'

    def tearDown(self):
        from nodeone.core.platform.events import clear_subscribers

        clear_subscribers()
        os.environ.pop('NODEONE_EVENT_BUS_SYNC', None)

    def test_wildcard_subscriber(self):
        from nodeone.core.platform.events import (
            EPOSONE_ORDER_CREATED,
            EPOSONE_ORDER_PAID,
            _handlers_for,
            subscribe,
        )

        hits: list[str] = []

        subscribe('eposone.order.*', lambda m: hits.append(m.event_type))
        subscribe(EPOSONE_ORDER_CREATED, lambda m: hits.append('exact'))

        handlers_created = _handlers_for(EPOSONE_ORDER_CREATED)
        handlers_paid = _handlers_for(EPOSONE_ORDER_PAID)
        handlers_sales = _handlers_for('sales.invoice.issued')

        self.assertEqual(len(handlers_created), 2)
        self.assertEqual(len(handlers_paid), 1)
        self.assertEqual(len(handlers_sales), 0)

        for fn in handlers_created:
            fn(
                SimpleNamespace(
                    event_type=EPOSONE_ORDER_CREATED,
                    payload={},
                )
            )
        self.assertIn(EPOSONE_ORDER_CREATED, hits)
        self.assertIn('exact', hits)


class TestEventBusDispatch(unittest.TestCase):
    def setUp(self):
        from nodeone.core.platform.events import clear_subscribers

        clear_subscribers()

    def tearDown(self):
        from nodeone.core.platform.events import clear_subscribers

        clear_subscribers()

    @patch('models.platform_events.PlatformDomainEvent')
    @patch('app.db')
    def test_dispatch_marks_dispatched(self, mock_db, mock_model):
        from models.platform_events import EVENT_STATUS_DISPATCHED

        from nodeone.core.platform.events import EPOSONE_ORDER_CREATED, dispatch_event_by_id, subscribe

        row = _fake_row()
        mock_model.query.get.return_value = row
        received: list[str] = []
        subscribe(EPOSONE_ORDER_CREATED, lambda m: received.append(m.event_type))

        ok = dispatch_event_by_id(1)
        self.assertTrue(ok)
        self.assertEqual(row.status, EVENT_STATUS_DISPATCHED)
        self.assertIsNotNone(row.dispatched_at)
        self.assertEqual(received, [EPOSONE_ORDER_CREATED])
        mock_db.session.commit.assert_called()

    @patch('nodeone.core.platform.events.publish_domain_event')
    def test_eposone_publish_helpers(self, mock_publish):
        from nodeone.core.platform.events import EPOSONE_ORDER_CREATED

        from nodeone.modules.eposone.events import publish_order_created

        publish_order_created(1, order_ref='T-99', total=10.5)
        mock_publish.assert_called_once()
        args, kwargs = mock_publish.call_args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1], EPOSONE_ORDER_CREATED)
        self.assertEqual(args[2]['order_ref'], 'T-99')
        self.assertEqual(kwargs['source_app_id'], 'eposone')

    @patch('nodeone.core.platform.events.dispatch_event_by_id')
    @patch('models.platform_events.PlatformDomainEvent')
    @patch('app.db')
    def test_publish_sync_dispatch(self, mock_db, mock_model, mock_dispatch):
        from nodeone.core.platform.events import EPOSONE_ORDER_CREATED, publish_domain_event

        row = _fake_row(event_id=7)
        mock_model.return_value = row
        mock_model.query.get.return_value = row

        publish_domain_event(1, EPOSONE_ORDER_CREATED, {}, source_app_id='eposone', sync_dispatch=True)
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called()
        mock_dispatch.assert_called_once_with(7)


if __name__ == '__main__':
    unittest.main()
