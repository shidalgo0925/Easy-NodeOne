"""Tests worker de plataforma — Etapa 8."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPlatformWorkerCycle(unittest.TestCase):
    @patch('nodeone.modules.eposone.sync_handlers.process_eposone_sync_queue', return_value=4)
    @patch('nodeone.core.platform.events.dispatch_pending_events', return_value=3)
    @patch('nodeone.core.platform.events.retry_failed_events', return_value=1)
    def test_run_platform_worker_cycle(self, mock_retry, mock_dispatch, mock_sync):
        from nodeone.core.platform.worker import run_platform_worker_cycle

        result = run_platform_worker_cycle(
            event_limit=10,
            sync_limit=5,
            organization_id=7,
            retry_failed=True,
            process_sync=True,
        )
        self.assertEqual(result.events_dispatched, 3)
        self.assertEqual(result.events_retried, 1)
        self.assertEqual(result.sync_processed, 4)
        mock_retry.assert_called_once_with(limit=10, organization_id=7)
        mock_dispatch.assert_called_once_with(limit=10, organization_id=7)
        mock_sync.assert_called_once_with(organization_id=7, limit=5)

    @patch('nodeone.modules.eposone.sync_handlers.process_eposone_sync_queue')
    @patch('nodeone.core.platform.events.dispatch_pending_events', return_value=2)
    @patch('nodeone.core.platform.events.retry_failed_events')
    def test_run_without_retry_or_sync(self, mock_retry, mock_dispatch, mock_sync):
        from nodeone.core.platform.worker import run_platform_worker_cycle

        result = run_platform_worker_cycle(
            retry_failed=False,
            process_sync=False,
        )
        self.assertEqual(result.events_dispatched, 2)
        self.assertEqual(result.events_retried, 0)
        self.assertEqual(result.sync_processed, 0)
        mock_retry.assert_not_called()
        mock_sync.assert_not_called()


class TestPlatformWorkerRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app as flask_app

        cls.app = flask_app
        cls.client = flask_app.test_client()

    def tearDown(self):
        os.environ.pop('NODEONE_PLATFORM_WORKER_TOKEN', None)

    def test_worker_route_registered(self):
        rules = {r.rule for r in self.app.url_map.iter_rules()}
        self.assertIn('/api/platform/sync/worker/cycle', rules)

    def test_worker_route_disabled_without_token(self):
        resp = self.client.post('/api/platform/sync/worker/cycle', json={})
        self.assertEqual(resp.status_code, 503)

    def test_worker_route_unauthorized_with_wrong_token(self):
        os.environ['NODEONE_PLATFORM_WORKER_TOKEN'] = 'secret-token'
        resp = self.client.post(
            '/api/platform/sync/worker/cycle',
            json={},
            headers={'X-Worker-Token': 'wrong'},
        )
        self.assertEqual(resp.status_code, 401)

    @patch('nodeone.core.platform.worker.run_platform_worker_cycle')
    def test_worker_route_runs_cycle(self, mock_run):
        from nodeone.core.platform.worker import PlatformWorkerResult

        os.environ['NODEONE_PLATFORM_WORKER_TOKEN'] = 'secret-token'
        mock_run.return_value = PlatformWorkerResult(
            events_dispatched=2,
            events_retried=1,
            sync_processed=3,
        )
        resp = self.client.post(
            '/api/platform/sync/worker/cycle',
            json={'event_limit': 20, 'organization_id': 1},
            headers={'Authorization': 'Bearer secret-token'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['result']['events_dispatched'], 2)
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
