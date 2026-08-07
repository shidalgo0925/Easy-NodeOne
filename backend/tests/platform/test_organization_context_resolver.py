"""Tests ADR-029 pending initial organization context."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPendingInitialOrganization(unittest.TestCase):
    def test_peek_respects_ttl(self):
        from nodeone.services.organization_context_resolver import (
            peek_pending_initial_organization,
        )

        fresh = SimpleNamespace(
            pending_initial_organization_id=42,
            pending_initial_organization_at=datetime.utcnow(),
        )
        self.assertEqual(peek_pending_initial_organization(fresh), 42)

        stale = SimpleNamespace(
            pending_initial_organization_id=42,
            pending_initial_organization_at=datetime.utcnow() - timedelta(days=30),
        )
        self.assertIsNone(peek_pending_initial_organization(stale))

    def test_consume_clears_row(self):
        from nodeone.services import organization_context_resolver as ocr

        user = SimpleNamespace(
            id=7,
            pending_initial_organization_id=99,
            pending_initial_organization_at=datetime.utcnow(),
        )
        row = SimpleNamespace(
            pending_initial_organization_id=99,
            pending_initial_organization_at=user.pending_initial_organization_at,
        )
        mock_q = MagicMock()
        mock_q.get.return_value = row
        with patch.object(ocr, 'peek_pending_initial_organization', return_value=99):
            with patch('models.users.User') as User:
                User.query = mock_q
                with patch('nodeone.core.db.db') as db:
                    db.session.commit = MagicMock()
                    out = ocr.consume_pending_initial_organization(user)
        self.assertEqual(out, 99)
        self.assertIsNone(row.pending_initial_organization_id)
        self.assertIsNone(user.pending_initial_organization_id)


if __name__ == '__main__':
    unittest.main()
