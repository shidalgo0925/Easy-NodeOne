"""Infra V6 — Commercial Policy Engine (herencia, lifecycle, validación, stub)."""

from __future__ import annotations

import unittest

from nodeone.modules.eposone.commercial_policy_service import (
    POLICY_TYPES,
    CommercialPolicyValidationError,
    resolve_scope_chain,
    validate_policy_payload,
)
from nodeone.modules.eposone.order_calculation_engine import OrderCalculationEngine


class TestCommercialPolicyScope(unittest.TestCase):
    def test_scope_chain_most_specific_first(self):
        chain = resolve_scope_chain(
            organization_id=5,
            branch_ref='BR-1',
            pos_ref='POS-1',
            register_ref='CAJA-1',
        )
        self.assertEqual(
            chain,
            [
                ('register', 'CAJA-1'),
                ('pos', 'POS-1'),
                ('branch', 'BR-1'),
                ('organization', '5'),
            ],
        )

    def test_scope_chain_org_only(self):
        chain = resolve_scope_chain(organization_id=9)
        self.assertEqual(chain, [('organization', '9')])

    def test_policy_types_cover_v6_instruction(self):
        for required in (
            'fiscal',
            'tips',
            'payments',
            'receipt',
            'commercial_config',
            'promotion',
        ):
            self.assertIn(required, POLICY_TYPES)


class TestPublishValidation(unittest.TestCase):
    def test_percent_out_of_range(self):
        with self.assertRaises(CommercialPolicyValidationError) as ctx:
            validate_policy_payload('tips', {'tip_percent': 150})
        self.assertIn('percent_out_of_range', str(ctx.exception))

    def test_percent_ok(self):
        validate_policy_payload('tips', {'tip_percent': 10})
        validate_policy_payload('fiscal', {'rate': 0.07})

    def test_dates_inverted(self):
        from datetime import datetime

        with self.assertRaises(CommercialPolicyValidationError):
            validate_policy_payload(
                'fiscal',
                {},
                valid_from=datetime(2026, 7, 20),
                valid_to=datetime(2026, 7, 1),
            )

    def test_payload_dates_inverted(self):
        with self.assertRaises(CommercialPolicyValidationError):
            validate_policy_payload(
                'promotion',
                {'valid_from': '2026-08-01T00:00:00Z', 'valid_to': '2026-07-01T00:00:00Z'},
            )


class TestOrderCalculationEngineStub(unittest.TestCase):
    def test_calculate_is_not_implemented_stub(self):
        result = OrderCalculationEngine.calculate(1, {'lines': []}, branch_ref='BR-1')
        self.assertEqual(result.status, 'not_implemented')
        self.assertTrue(result.detail.get('ready_for_policies'))


class TestInheritanceSelection(unittest.TestCase):
    def test_register_overrides_organization(self):
        chain = resolve_scope_chain(
            organization_id=1, branch_ref='B', pos_ref='P', register_ref='R'
        )
        assignments = {
            ('fiscal', 'organization', '1'): 'ORG-FISCAL',
            ('fiscal', 'register', 'R'): 'CAJA-FISCAL',
        }
        chosen = None
        for scope_type, scope_ref in chain:
            key = ('fiscal', scope_type, scope_ref)
            if key in assignments:
                chosen = assignments[key]
                break
        self.assertEqual(chosen, 'CAJA-FISCAL')


if __name__ == '__main__':
    unittest.main()
