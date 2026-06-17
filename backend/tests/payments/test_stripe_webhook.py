"""Tests unitarios: webhook y helpers Stripe."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestStripeWebhookHelpers(unittest.TestCase):
    def test_pi_id_from_payment_intent_event(self):
        from nodeone.services.stripe_webhook import _stripe_pi_id_from_event

        parsed = {
            'type': 'payment_intent.succeeded',
            'data': {'object': {'id': 'pi_abc123'}},
        }
        self.assertEqual(_stripe_pi_id_from_event(parsed), 'pi_abc123')

    def test_pi_id_from_charge_refunded(self):
        from nodeone.services.stripe_webhook import _stripe_pi_id_from_event

        parsed = {
            'type': 'charge.refunded',
            'data': {'object': {'payment_intent': 'pi_xyz'}},
        }
        self.assertEqual(_stripe_pi_id_from_event(parsed), 'pi_xyz')

    def test_stripe_credentials_configured(self):
        from nodeone.services.stripe_webhook import stripe_credentials_configured

        cfg = MagicMock()
        cfg.get_stripe_publishable_key.return_value = 'pk_live_abc'
        cfg.get_stripe_secret_key.return_value = 'sk_live_abc'
        self.assertTrue(stripe_credentials_configured(cfg))

        cfg.get_stripe_secret_key.return_value = 'sk_test_your_'
        self.assertFalse(stripe_credentials_configured(cfg))


class TestStripeWebhookDispatch(unittest.TestCase):
    @patch('nodeone.services.stripe_webhook.handle_payment_intent_succeeded')
    def test_dispatch_succeeded(self, mock_ok):
        from nodeone.services.stripe_webhook import dispatch_stripe_webhook_event

        event = {'type': 'payment_intent.succeeded', 'id': 'evt_1', 'data': {'object': {'id': 'pi_1'}}}
        dispatch_stripe_webhook_event(event)
        mock_ok.assert_called_once()

    @patch('nodeone.services.stripe_webhook.handle_payment_intent_failed')
    def test_dispatch_failed(self, mock_fail):
        from nodeone.services.stripe_webhook import dispatch_stripe_webhook_event

        event = {'type': 'payment_intent.payment_failed', 'id': 'evt_2', 'data': {'object': {'id': 'pi_2'}}}
        dispatch_stripe_webhook_event(event)
        mock_fail.assert_called_once()

    @patch('nodeone.services.stripe_webhook.handle_charge_refunded')
    def test_dispatch_refunded(self, mock_ref):
        from nodeone.services.stripe_webhook import dispatch_stripe_webhook_event

        event = {'type': 'charge.refunded', 'id': 'evt_3', 'data': {'object': {'payment_intent': 'pi_3'}}}
        dispatch_stripe_webhook_event(event)
        mock_ref.assert_called_once()


class TestPaymentMethodsCatalog(unittest.TestCase):
    def test_stripe_in_payment_methods(self):
        from payment_processors import PAYMENT_METHODS

        self.assertIn('stripe', PAYMENT_METHODS)

    def test_iius_profile_enables_stripe(self):
        from nodeone.services.organization_payment_methods import PAYMENT_PROFILES

        self.assertTrue(PAYMENT_PROFILES['international']['enabled']['stripe'])


if __name__ == '__main__':
    unittest.main()
