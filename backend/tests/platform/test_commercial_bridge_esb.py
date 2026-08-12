"""Bridge comercial ESB ↔ EN1 — bootstrap / checkout promo / entitlement."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestCommercialBridgeUnit(unittest.TestCase):
    def test_require_product_rejects_unknown(self):
        from nodeone.modules.commercial_bridge.service import (
            CommercialBridgeError,
            _require_product,
        )

        with patch(
            'nodeone.core.platform.product_registry.ProductRegistry.get', return_value=None
        ):
            with self.assertRaises(CommercialBridgeError) as ctx:
                _require_product('esecurebroker')
            self.assertEqual(ctx.exception.code, 'unknown_product')

    def test_require_product_rejects_other_codes(self):
        from nodeone.modules.commercial_bridge.service import (
            CommercialBridgeError,
            _require_product,
        )

        with self.assertRaises(CommercialBridgeError) as ctx:
            _require_product('eposone')
        self.assertEqual(ctx.exception.code, 'product_not_supported')

    def test_validate_promo_requires_100(self):
        from nodeone.modules.commercial_bridge.service import (
            CommercialBridgeError,
            _validate_promo,
        )

        row = SimpleNamespace(
            code='HALF',
            discount_type='percentage',
            value=50.0,
            id=1,
            can_use=lambda user_id=None: (True, 'ok'),
        )
        mock_q = MagicMock()
        mock_q.filter.return_value.first.return_value = row
        mock_q.filter_by.return_value.first.return_value = row
        with patch('models.events.DiscountCode') as MockDC:
            MockDC.query = mock_q
            with self.assertRaises(CommercialBridgeError) as ctx:
                _validate_promo(code='HALF', user_id=1)
            self.assertEqual(ctx.exception.code, 'promo_not_complimentary')

    def test_validate_promo_100_ok(self):
        from nodeone.modules.commercial_bridge.service import _validate_promo

        row = SimpleNamespace(
            code='ESB-DEV-100',
            discount_type='percentage',
            value=100.0,
            id=9,
            can_use=lambda user_id=None: (True, 'ok'),
        )
        mock_q = MagicMock()
        mock_q.filter.return_value.first.return_value = row
        with patch('models.events.DiscountCode') as MockDC:
            MockDC.query = mock_q
            out = _validate_promo(code='ESB-DEV-100', user_id=1)
            self.assertEqual(out['final_amount'], 0.0)
            self.assertEqual(out['promo_code'], 'ESB-DEV-100')
    def test_get_entitlement_not_entitled(self):
        from nodeone.modules.commercial_bridge.service import get_entitlement

        customer = SimpleNamespace(id=5)
        with patch(
            'nodeone.modules.commercial_bridge.service._require_product',
            return_value='esecurebroker',
        ), patch(
            'nodeone.core.platform.ets_provider.ets_provider_organization_id', return_value=1
        ), patch(
            'models.ets_commercial_customer.EtsCommercialCustomer'
        ) as MockCust, patch(
            'models.ets_product_subscription.EtsProductSubscription'
        ) as MockSub:
            MockCust.query.filter_by.return_value.first.return_value = customer
            MockSub.query.filter_by.return_value.first.return_value = None
            out = get_entitlement(product_code='esecurebroker', customer_id=5)
            self.assertFalse(out['entitled'])
            self.assertEqual(out['state'], 'none')

    def test_blueprint_routes_registered(self):
        from app import app as flask_app

        self.assertIn('commercial_bridge', flask_app.blueprints)
        rules = {r.rule for r in flask_app.url_map.iter_rules()}
        self.assertIn('/api/v1/commercial/bootstrap', rules)
        self.assertIn('/api/v1/commercial/checkout', rules)
        self.assertIn('/api/v1/commercial/entitlement', rules)


if __name__ == '__main__':
    unittest.main()
