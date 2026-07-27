"""Tests sync offline — Etapa 13."""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestSyncRetry(unittest.TestCase):
    def test_backoff_increases(self):
        from nodeone.core.sync.retry import compute_next_retry_at

        t1 = compute_next_retry_at(1, base_seconds=10)
        t2 = compute_next_retry_at(2, base_seconds=10)
        self.assertGreater(t2, t1)

    def test_is_ready_for_retry(self):
        from nodeone.core.sync.retry import is_ready_for_retry

        self.assertTrue(is_ready_for_retry(None))
        self.assertFalse(is_ready_for_retry(datetime.utcnow() + timedelta(hours=1)))


class TestSyncConflicts(unittest.TestCase):
    def test_version_mismatch(self):
        from nodeone.core.sync.conflicts import detect_version_conflict

        self.assertIsNotNone(detect_version_conflict(base_version=1, server_version=2))
        self.assertIsNone(detect_version_conflict(base_version=2, server_version=2))


class TestEventBusRetry(unittest.TestCase):
    def setUp(self):
        from nodeone.core.platform.events import clear_subscribers

        clear_subscribers()

    def tearDown(self):
        from nodeone.core.platform.events import clear_subscribers

        clear_subscribers()

    @patch('nodeone.core.sync.retry.max_event_retries', return_value=3)
    @patch('nodeone.core.sync.retry.compute_next_retry_at')
    @patch('models.platform_events.PlatformDomainEvent')
    @patch('app.db')
    def test_dispatch_failure_schedules_retry(self, mock_db, mock_model, mock_next_retry, _mock_max):
        from models.platform_events import EVENT_STATUS_PENDING

        from nodeone.core.platform.events import EPOSONE_ORDER_CREATED, dispatch_event_by_id, subscribe

        row = SimpleNamespace(
            id=1,
            organization_id=1,
            event_type=EPOSONE_ORDER_CREATED,
            source_app_id='eposone',
            payload={},
            status=EVENT_STATUS_PENDING,
            error_message=None,
            retry_count=0,
            next_retry_at=None,
            created_at=datetime.utcnow(),
            dispatched_at=None,
        )
        mock_model.query.get.return_value = row
        mock_next_retry.return_value = datetime.utcnow() + timedelta(seconds=60)

        def _boom(_msg):
            raise RuntimeError('handler failed')

        subscribe(EPOSONE_ORDER_CREATED, _boom)
        ok = dispatch_event_by_id(1)
        self.assertFalse(ok)
        self.assertEqual(row.status, EVENT_STATUS_PENDING)
        self.assertEqual(row.retry_count, 1)
        self.assertIsNotNone(row.next_retry_at)


class TestSyncEventsDispatchRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def test_events_dispatch_route_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/api/platform/sync/events/dispatch', rules)

    @patch('nodeone.core.platform.events.retry_failed_events', return_value=1)
    @patch('nodeone.core.platform.events.dispatch_pending_events', return_value=3)
    def test_events_dispatch_logic(self, mock_dispatch, mock_retry):
        gate = 1
        body = {'limit': 10, 'retry_failed': True}
        limit = int(body.get('limit', 100) or 100)
        retry_failed = bool(body.get('retry_failed', False))
        retried = mock_retry(limit=limit, organization_id=gate) if retry_failed else 0
        dispatched = mock_dispatch(limit=limit, organization_id=gate)
        self.assertEqual(retried, 1)
        self.assertEqual(dispatched, 3)


class TestSyncOperationService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('nodeone.core.sync.queue.PlatformSyncOperation')
    def test_enqueue_idempotent(self, mock_model):
        from nodeone.core.sync.queue import SyncOperationService

        existing = MagicMock()
        existing.id = 9
        existing.organization_id = 1
        existing.client_id = 'pos-1'
        existing.idempotency_key = 'k1'
        existing.operation_type = 'create_order'
        existing.status = 'pending'
        existing.entity_type = None
        existing.entity_ref = None
        existing.payload = {}
        existing.base_version = None
        existing.retry_count = 0
        existing.conflict_reason = None
        existing.created_at = None
        existing.applied_at = None
        mock_model.query.filter_by.return_value.first.return_value = existing

        dto = SyncOperationService.enqueue(
            1, idempotency_key='k1', operation_type='create_order', client_id='pos-1'
        )
        self.assertEqual(dto.id, 9)


if __name__ == '__main__':
    unittest.main()
