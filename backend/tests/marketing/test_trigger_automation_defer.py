"""NODEONE_AUTOMATION_DEFER_TO_COMM_ENGINE evita cola legacy si hay reglas."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestTriggerAutomationDefer(unittest.TestCase):
    def test_defer_skips_when_rules_exist(self):
        from app import app, db
        from models.communications import AutomationFlow, EmailQueueItem, MarketingTemplate
        from models.communication_rules import CommunicationEvent, CommunicationRule

        with app.app_context():
            before = EmailQueueItem.query.count()
            tpl = MarketingTemplate(name='defer_tpl', html='<p>x</p>', variables='[]')
            db.session.add(tpl)
            db.session.flush()
            flow = AutomationFlow(
                name='f',
                trigger_event='member_created',
                template_id=tpl.id,
                delay_hours=0,
                active=True,
            )
            db.session.add(flow)
            db.session.flush()

            ev = CommunicationEvent.query.filter_by(code='member_created').first()
            if not ev:
                db.session.rollback()
                self.skipTest('Sin communication_event member_created')
                return

            rule = CommunicationRule(
                event_id=ev.id,
                organization_id=None,
                channel='email',
                marketing_template_id=tpl.id,
                enabled=True,
                delay_minutes=0,
                is_marketing=True,
                respect_user_prefs=True,
                priority=10,
            )
            db.session.add(rule)
            db.session.commit()

            from app import User

            u = (
                User.query.filter_by(email_marketing_status='subscribed', is_active=True)
                .filter(User.organization_id.isnot(None))
                .first()
            )
            if not u:
                db.session.delete(rule)
                db.session.delete(flow)
                db.session.delete(tpl)
                db.session.commit()
                self.skipTest('Sin usuario subscribed')
                return

            with patch.dict(os.environ, {'NODEONE_AUTOMATION_DEFER_TO_COMM_ENGINE': '1'}):
                from _app.modules.marketing.service import trigger_automation

                trigger_automation('member_created', u.id, base_url='https://example.com')

            after = EmailQueueItem.query.count()
            db.session.delete(rule)
            db.session.delete(flow)
            db.session.delete(tpl)
            db.session.commit()
            self.assertEqual(after, before, 'defer=1 no debería encolar EmailQueueItem')


if __name__ == '__main__':
    unittest.main()
