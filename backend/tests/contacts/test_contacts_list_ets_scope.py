"""Listado Clientes: ETS solo en org proveedor; labels sin dossier."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestEtsBuyersListScope(unittest.TestCase):
    def test_sa_on_non_provider_org_does_not_include_ets(self):
        from nodeone.services.commercial_customer_visibility import (
            include_ets_buyers_on_contact_list,
        )

        with patch(
            'nodeone.services.commercial_customer_visibility.ets_provider_organization_id',
            return_value=1,
        ):
            self.assertFalse(include_ets_buyers_on_contact_list(12))
            self.assertFalse(include_ets_buyers_on_contact_list(9))
            self.assertTrue(include_ets_buyers_on_contact_list(1))


class TestProductLabelsBatch(unittest.TestCase):
    def test_labels_do_not_call_commercial_dossier(self):
        from nodeone.services import commercial_customer_visibility as vis

        customer_q = MagicMock()
        customer_q.filter.return_value.with_entities.return_value.all.return_value = [
            (10, 100),
        ]
        contract_q = MagicMock()
        contract_q.filter.return_value.with_entities.return_value.order_by.return_value.all.return_value = [
            (10, 'eposone'),
        ]

        with patch.object(
            vis, 'commercial_dossier', side_effect=AssertionError('list must not load dossier')
        ):
            with patch.object(vis, 'ets_provider_organization_id', return_value=1):
                with patch.object(vis, '_product_name', return_value='EPosOne'):
                    with patch(
                        'models.ets_commercial_customer.EtsCommercialCustomer'
                    ) as cust_cls:
                        with patch(
                            'models.ets_commercial_contract.EtsCommercialContract'
                        ) as contract_cls:
                            cust_cls.query = customer_q
                            contract_cls.query = contract_q
                            out = vis.product_labels_by_contact_id([100, 101])

        self.assertEqual(out, {100: ['EPosOne']})

    def test_dossier_for_contact_still_uses_commercial_dossier(self):
        from nodeone.services import commercial_customer_visibility as vis

        customer = MagicMock()
        customer.id = 10
        customer.contact_id = 100
        expected = {'customer': customer, 'products': [{'product_code': 'eposone'}]}

        with patch.object(vis, 'ets_provider_organization_id', return_value=1):
            with patch(
                'models.ets_commercial_customer.EtsCommercialCustomer'
            ) as cust_cls:
                cust_cls.query.filter_by.return_value.first.return_value = customer
                with patch.object(vis, 'commercial_dossier', return_value=expected) as dossier:
                    out = vis.dossier_for_contact(100)

        self.assertIs(out, expected)
        dossier.assert_called_once_with(customer)


if __name__ == '__main__':
    unittest.main()
