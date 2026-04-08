"""Smoke: blueprints de pagos registrados tras importar la app (unittest stdlib)."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestPaymentBlueprintRoutes(unittest.TestCase):
    def test_payments_blueprint_endpoints_registered(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'payments_checkout.payments_history',
            'payments_checkout.service_payment_success_callback',
            'payments_checkout.payment_status',
            'payments_checkout.payment_success',
            'payments_checkout.stripe_webhook',
            'payments_admin.admin_payments',
            'payments_admin.admin_payment_review',
            'payments_admin.api_approve_payment',
            'payments_admin.api_reject_payment',
            'payments_admin.api_payment_config',
        }
        missing = required - endpoints
        self.assertFalse(missing, f'Faltan endpoints: {sorted(missing)}')

    def test_payments_routes_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('payments_checkout.payments_history'), '/payments/history')
        self.assertEqual(
            by_ep.get('payments_checkout.payment_status'),
            '/payments/status/<int:payment_id>',
        )
        self.assertEqual(
            by_ep.get('payments_checkout.service_payment_success_callback'),
            '/api/payments/<int:payment_id>/success',
        )
        self.assertEqual(by_ep.get('payments_admin.admin_payments'), '/admin/payments')


if __name__ == '__main__':
    unittest.main()
