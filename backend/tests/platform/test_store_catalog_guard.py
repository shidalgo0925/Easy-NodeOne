"""Tienda /services: sales o appointments + visibilidad universal de catálogo."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class StoreCatalogGuardTests(unittest.TestCase):
    def test_org_store_catalog_enabled_sales_or_appointments(self):
        from saas_features import org_store_catalog_enabled

        with patch('app.has_saas_module_enabled') as mock_has:
            mock_has.side_effect = lambda oid, code: code == 'sales'
            self.assertTrue(org_store_catalog_enabled(7))

            mock_has.side_effect = lambda oid, code: code == 'appointments'
            self.assertTrue(org_store_catalog_enabled(7))

            mock_has.side_effect = lambda oid, code: False
            self.assertFalse(org_store_catalog_enabled(7))


class StoreVisibilityTests(unittest.TestCase):
    """Vitrina: catálogo activo para todos; no filtrar por precio 0 ni plan basic."""

    def _svc(self, **kwargs):
        defaults = {
            'id': 10,
            'membership_type': 'basic',
            'base_price': 0,
            'service_type': 'AGENDABLE',
            'appointment_type_id': None,
            'pricing_for_membership': MagicMock(return_value={'is_included': False, 'price': 0}),
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_anon_sees_catalog(self):
        from _app.modules.services.service import _should_show_service_in_store

        self.assertTrue(
            _should_show_service_in_store(
                self._svc(), user=None, membership_type='basic', open_contract_ids=set()
            )
        )

    def test_logged_in_sees_zero_price_basic_catalog(self):
        from _app.modules.services.service import _should_show_service_in_store

        user = SimpleNamespace(is_authenticated=True)
        self.assertTrue(
            _should_show_service_in_store(
                self._svc(), user=user, membership_type='basic', open_contract_ids=set()
            )
        )

    def test_hides_open_contract(self):
        from _app.modules.services.service import _should_show_service_in_store

        user = SimpleNamespace(is_authenticated=True)
        self.assertFalse(
            _should_show_service_in_store(
                self._svc(id=42),
                user=user,
                membership_type='basic',
                open_contract_ids={42},
            )
        )

    def test_hides_only_explicit_plan_included(self):
        from _app.modules.services.service import _should_show_service_in_store

        user = SimpleNamespace(is_authenticated=True)
        svc = self._svc(
            pricing_for_membership=MagicMock(return_value={'is_included': True, 'price': 0})
        )
        self.assertFalse(
            _should_show_service_in_store(
                svc, user=user, membership_type='pro', open_contract_ids=set()
            )
        )


if __name__ == '__main__':
    unittest.main()
