"""Bridge comercial ESB ↔ EN1 — Slice C1: planes, pricing, idempotency, entitlement."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEsbCommercialPlans(unittest.TestCase):
    def test_catalog_codes_and_prices(self):
        from nodeone.core.platform.esecurebroker_commercial_plans import (
            get_esb_list_price,
            list_esb_plan_codes,
        )

        self.assertEqual(
            list_esb_plan_codes(),
            ['individual', 'office', 'broker', 'enterprise'],
        )
        self.assertEqual(get_esb_list_price('individual'), 55.0)
        self.assertEqual(get_esb_list_price('office'), 129.0)
        self.assertEqual(get_esb_list_price('broker'), 229.0)
        self.assertIsNone(get_esb_list_price('enterprise'))
        self.assertIsNone(get_esb_list_price('starter'))

    def test_no_eposone_codes(self):
        from nodeone.core.platform.esecurebroker_commercial_plans import normalize_esb_plan_code

        self.assertIsNone(normalize_esb_plan_code('starter'))
        self.assertIsNone(normalize_esb_plan_code('business'))

    def test_entitlement_template_office_seats(self):
        from nodeone.core.platform.entitlement_plans import get_plan_template

        tpl = get_plan_template('esecurebroker', 'office')
        self.assertEqual(tpl['resource_limits']['internal_seats'], 15)
        self.assertIsNone(tpl['resource_limits']['producer_seats'])

    def test_entitlement_template_broker_null_seats(self):
        from nodeone.core.platform.entitlement_plans import get_plan_template

        tpl = get_plan_template('esecurebroker', 'broker')
        self.assertIsNone(tpl['resource_limits']['internal_seats'])
        self.assertIsNone(tpl['resource_limits']['producer_seats'])
        self.assertTrue(tpl['features']['producers_network'])


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

    def test_invalid_plan_rejects_starter(self):
        from nodeone.modules.commercial_bridge.service import (
            CommercialBridgeError,
            _require_esb_plan,
        )

        with self.assertRaises(CommercialBridgeError) as ctx:
            _require_esb_plan('starter', for_checkout=True)
        self.assertEqual(ctx.exception.code, 'invalid_plan')

    def test_enterprise_requires_quote(self):
        from nodeone.modules.commercial_bridge.service import (
            CommercialBridgeError,
            _require_esb_plan,
        )

        with self.assertRaises(CommercialBridgeError) as ctx:
            _require_esb_plan('enterprise', for_checkout=True)
        self.assertEqual(ctx.exception.code, 'plan_requires_quote')

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
                _validate_promo(code='HALF', user_id=1, list_amount=55.0)
            self.assertEqual(ctx.exception.code, 'promo_not_complimentary')

    def test_validate_promo_100_uses_list_price(self):
        from nodeone.modules.commercial_bridge.service import _validate_promo

        row = SimpleNamespace(
            code='ESB-DEV-100',
            discount_type='percentage',
            value=100.0,
            id=9,
            can_use=lambda user_id=None: (True, 'ok'),
            applies_to_product=lambda pc: True,
        )
        mock_q = MagicMock()
        mock_q.filter.return_value.first.return_value = row
        with patch('models.events.DiscountCode') as MockDC:
            MockDC.query = mock_q
            out = _validate_promo(code='ESB-DEV-100', user_id=1, list_amount=55.0)
            self.assertEqual(out['final_amount'], 0.0)
            self.assertEqual(out['list_amount'], 55.0)
            self.assertEqual(out['discount_amount'], 55.0)
            self.assertEqual(out['promo_code'], 'ESB-DEV-100')

        with patch('models.events.DiscountCode') as MockDC:
            MockDC.query = mock_q
            out129 = _validate_promo(code='ESB-DEV-100', user_id=1, list_amount=129.0)
            self.assertEqual(out129['list_amount'], 129.0)
            self.assertEqual(out129['discount_amount'], 129.0)

        with patch('models.events.DiscountCode') as MockDC:
            MockDC.query = mock_q
            out229 = _validate_promo(code='ESB-DEV-100', user_id=1, list_amount=229.0)
            self.assertEqual(out229['list_amount'], 229.0)
            self.assertEqual(out229['discount_amount'], 229.0)

    def test_get_entitlement_includes_limits_features(self):
        from nodeone.modules.commercial_bridge.service import get_entitlement

        customer = SimpleNamespace(id=5)
        sub = SimpleNamespace(
            id=24,
            status='active',
            metadata_json=json.dumps({'plan_code': 'office'}),
        )
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
            MockSub.query.filter_by.return_value.first.return_value = sub
            out = get_entitlement(product_code='esecurebroker', customer_id=5)
            self.assertTrue(out['entitled'])
            self.assertEqual(out['plan_code'], 'office')
            self.assertEqual(out['limits']['internal_seats'], 15)
            self.assertIn('features', out)

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

    def test_idempotency_hash_stable(self):
        from nodeone.modules.commercial_bridge.idempotency import (
            checkout_idempotency_payload,
            request_body_hash,
        )

        a = request_body_hash(
            checkout_idempotency_payload(
                {
                    'product_code': 'esecurebroker',
                    'plan_code': 'individual',
                    'customer_id': 6,
                    'promo_code': 'ESB-DEV-100',
                }
            )
        )
        b = request_body_hash(
            checkout_idempotency_payload(
                {
                    'promo_code': 'ESB-DEV-100',
                    'customer_id': 6,
                    'plan_code': 'individual',
                    'product_code': 'esecurebroker',
                }
            )
        )
        self.assertEqual(a, b)
        c = request_body_hash(
            checkout_idempotency_payload(
                {
                    'product_code': 'esecurebroker',
                    'plan_code': 'office',
                    'customer_id': 6,
                    'promo_code': 'ESB-DEV-100',
                }
            )
        )
        self.assertNotEqual(a, c)

    def test_blueprint_routes_registered(self):
        from app import app as flask_app

        self.assertIn('commercial_bridge', flask_app.blueprints)
        rules = {r.rule for r in flask_app.url_map.iter_rules()}
        self.assertIn('/api/v1/commercial/bootstrap', rules)
        self.assertIn('/api/v1/commercial/checkout', rules)
        self.assertIn('/api/v1/commercial/entitlement', rules)


if __name__ == '__main__':
    unittest.main()
