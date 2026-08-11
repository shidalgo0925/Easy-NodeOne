"""Tienda ETS: SERVICE_DIRECT + fulfill licencia post-pago."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestTiendaEtsBuyFlow(unittest.TestCase):
    def test_agendable_priced_no_link_is_service_direct(self):
        from nodeone.services.commercial_flow import (
            COMMERCIAL_FLOW_SERVICE_DIRECT,
            flow_cta_labels,
            resolve_commercial_flow_type,
        )

        svc = SimpleNamespace(
            service_type='AGENDABLE',
            external_link=None,
            appointment_type_id=None,
            base_price=50.0,
        )
        flow = resolve_commercial_flow_type(svc, {'is_included': False, 'final_price': 50.0})
        self.assertEqual(flow, COMMERCIAL_FLOW_SERVICE_DIRECT)
        label, _hint = flow_cta_labels(flow, svc)
        self.assertEqual(label, 'Comprar')

    def test_consultivo_still_quote(self):
        from nodeone.services.commercial_flow import (
            COMMERCIAL_FLOW_SERVICE_CONSULTATIVE,
            resolve_commercial_flow_type,
        )

        svc = SimpleNamespace(
            service_type='CONSULTIVO',
            external_link=None,
            appointment_type_id=None,
            base_price=50.0,
        )
        flow = resolve_commercial_flow_type(svc, {})
        self.assertEqual(flow, COMMERCIAL_FLOW_SERVICE_CONSULTATIVE)

    def test_registry_has_new_portal_products(self):
        from nodeone.core.platform.product_registry import reload_product_registry, ProductRegistry
        from nodeone.core.platform.product_context import SURFACE_PRODUCT

        reload_product_registry()
        for code in ('easyia', 'em', 'esecurebroker', 'eposone', 'epayroll'):
            d = ProductRegistry.get(code)
            self.assertIsNotNone(d, code)
            self.assertEqual(d.surface, SURFACE_PRODUCT, code)


class TestFulfillEtsLicense(unittest.TestCase):
    @patch('nodeone.services.payment_post_process.EntitlementService', create=True)
    def test_fulfill_activates_subscription(self, _unused):
        # Patch at import sites inside helper
        service = SimpleNamespace(id=30, program_slug='eposone')
        with patch(
            'nodeone.core.platform.product_registry.ProductRegistry.get'
        ) as mock_get, patch(
            'nodeone.core.platform.subscription_registry.SubscriptionRegistry.activate'
        ) as mock_act, patch(
            'nodeone.core.platform.entitlement_service.EntitlementService.ensure_for_subscription'
        ) as mock_ent, patch(
            'models.ets_product_entitlement.EtsProductEntitlement'
        ) as MockEnt:
            mock_get.return_value = SimpleNamespace(surface='product', code='eposone')
            MockEnt.query.filter_by.return_value.first.return_value = None
            from nodeone.services.payment_post_process import _fulfill_ets_license_from_service

            _fulfill_ets_license_from_service(service, 1)
            mock_act.assert_called_once_with(1, 'eposone')
            mock_ent.assert_called_once()
            self.assertEqual(mock_ent.call_args.kwargs.get('plan_code'), 'starter')

    def test_fulfill_skips_unknown_slug(self):
        service = SimpleNamespace(id=1, program_slug='not-a-product')
        with patch(
            'nodeone.core.platform.product_registry.ProductRegistry.get', return_value=None
        ) as mock_get, patch(
            'nodeone.core.platform.subscription_registry.SubscriptionRegistry.activate'
        ) as mock_act:
            from nodeone.services.payment_post_process import _fulfill_ets_license_from_service

            _fulfill_ets_license_from_service(service, 1)
            mock_get.assert_called_once_with('not-a-product')
            mock_act.assert_not_called()

    def test_fulfill_preserves_existing_plan(self):
        service = SimpleNamespace(id=28, program_slug='eposone')
        existing = SimpleNamespace(plan_code='business')
        with patch(
            'nodeone.core.platform.product_registry.ProductRegistry.get',
            return_value=SimpleNamespace(surface='product'),
        ), patch(
            'nodeone.core.platform.subscription_registry.SubscriptionRegistry.activate'
        ) as mock_act, patch(
            'nodeone.core.platform.entitlement_service.EntitlementService.ensure_for_subscription'
        ) as mock_ent, patch(
            'models.ets_product_entitlement.EtsProductEntitlement'
        ) as MockEnt:
            MockEnt.query.filter_by.return_value.first.return_value = existing
            from nodeone.services.payment_post_process import _fulfill_ets_license_from_service

            _fulfill_ets_license_from_service(service, 1)
            mock_act.assert_called_once_with(1, 'eposone')
            self.assertEqual(mock_ent.call_args.kwargs.get('plan_code'), 'business')


if __name__ == '__main__':
    unittest.main()
