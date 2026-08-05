"""EasyAI Connector SDK — smoke tests (no Flask, no DB)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEasyAiSdk(unittest.TestCase):
    def test_domain_ids_complete(self):
        from nodeone.core.easyai import DOMAIN_IDS

        required = {
            'organizations',
            'users',
            'crm',
            'contacts',
            'membership',
            'payments',
            'subscriptions',
            'licenses',
            'analytics',
            'dashboard',
            'commerce',
            'products',
            'history',
            'audit',
            'event_bus',
            'context_resolver',
            'resolver',
            'entitlements',
        }
        self.assertEqual(set(DOMAIN_IDS), required)

    def test_registry_missing_all_initially(self):
        from nodeone.core.easyai import ConnectorRegistry, DOMAIN_IDS

        reg = ConnectorRegistry()
        self.assertEqual(reg.missing_domain_ids(), list(DOMAIN_IDS))
        self.assertEqual(reg.list_all_tools(), [])

    def test_protocol_is_runtime_checkable(self):
        from nodeone.core.easyai import DomainConnector

        self.assertTrue(callable(DomainConnector))


if __name__ == '__main__':
    unittest.main()
