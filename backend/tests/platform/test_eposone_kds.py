"""Tests KDS EPosOne — Etapa 15."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestKdsService(unittest.TestCase):
    def test_ticket_transitions_constants(self):
        from nodeone.modules.eposone.kds_service import KDS_TICKET_PENDING, KDS_TICKET_TRANSITIONS

        self.assertIn('preparing', KDS_TICKET_TRANSITIONS[KDS_TICKET_PENDING])

    @patch('nodeone.modules.eposone.kds_service.AuditService.publish_domain_event')
    @patch('app.db')
    @patch('nodeone.modules.eposone.kds_service.EposoneKdsTicket')
    @patch('nodeone.modules.eposone.kds_service.CoreCommercialOrder')
    @patch('nodeone.modules.eposone.kds_service.KdsService.ensure_default_station')
    def test_create_tickets_for_order(
        self, mock_station, mock_order_cls, mock_ticket_cls, mock_db, mock_publish
    ):
        from nodeone.modules.eposone.kds_service import KdsService

        order = MagicMock()
        order.id = 5
        order.order_ref = 'POS-0001'
        order.lines = [MagicMock(description='Taco', quantity=2.0)]
        mock_order_cls.query.filter_by.return_value.first.return_value = order
        mock_ticket_cls.query.filter_by.return_value.first.return_value = None
        mock_station.return_value = MagicMock(id=1)

        ticket = MagicMock()
        ticket.id = 10
        ticket.organization_id = 1
        ticket.order_id = 5
        ticket.order_ref = 'POS-0001'
        ticket.station_type = 'kitchen'
        ticket.status = 'pending'
        ticket.priority = 0
        ticket.created_at = None
        ticket.ready_at = None
        ticket.lines = [MagicMock(description='Taco', quantity=2.0, status='pending')]
        mock_ticket_cls.return_value = ticket

        items = KdsService.create_tickets_for_order(1, 5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].order_ref, 'POS-0001')
        mock_publish.assert_called_once()


class TestEPosOneKdsSections(unittest.TestCase):
    def test_kds_section_registered(self):
        from nodeone.modules.eposone.sections import EPOSONE_SECTION_SLUGS

        self.assertIn('kds', EPOSONE_SECTION_SLUGS)


if __name__ == '__main__':
    unittest.main()
