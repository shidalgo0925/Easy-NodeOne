"""Sincronización NotificationSettings → CommunicationRule."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestNotificationSettingsSync(unittest.TestCase):
    def test_sync_updates_matching_event_rules(self):
        from app import app, db
        from models.communication_rules import CommunicationEvent, CommunicationRule
        from nodeone.services.notification_settings_sync import (
            sync_notification_type_to_communication_rules,
        )

        with app.app_context():
            ev = CommunicationEvent.query.filter_by(code='welcome').first()
            if not ev:
                self.skipTest('Sin communication_event welcome')
            CommunicationRule.query.filter_by(event_id=ev.id).delete(synchronize_session=False)
            db.session.add(
                CommunicationRule(
                    event_id=ev.id,
                    organization_id=None,
                    channel='email',
                    marketing_template_id=None,
                    enabled=True,
                    delay_minutes=0,
                    is_marketing=False,
                    respect_user_prefs=True,
                    priority=10,
                )
            )
            db.session.commit()

            n = sync_notification_type_to_communication_rules('welcome', False)
            self.assertGreaterEqual(n, 1)
            r = CommunicationRule.query.filter_by(event_id=ev.id).first()
            self.assertFalse(r.enabled)

            sync_notification_type_to_communication_rules('welcome', True)
            db.session.refresh(r)
            self.assertTrue(r.enabled)

            db.session.delete(r)
            db.session.commit()

    def test_reverse_sync_updates_legacy_when_any_rule_active(self):
        from app import NotificationSettings, app, db
        from models.communication_rules import CommunicationEvent, CommunicationRule
        from nodeone.services.notification_settings_sync import (
            sync_event_rules_to_notification_settings,
        )

        code = '__test_legacy_rev_sync__'
        with app.app_context():
            ev_old = CommunicationEvent.query.filter_by(code=code).first()
            if ev_old:
                CommunicationRule.query.filter_by(event_id=ev_old.id).delete(synchronize_session=False)
                db.session.delete(ev_old)
            NotificationSettings.query.filter_by(notification_type=code).delete(synchronize_session=False)
            db.session.commit()

            ev = CommunicationEvent(
                code=code, name='test', description='test', category='system'
            )
            db.session.add(ev)
            db.session.flush()
            ns = NotificationSettings(
                notification_type=code,
                name='test',
                description='test',
                category='system',
                enabled=True,
            )
            db.session.add(ns)
            db.session.commit()

            db.session.add(
                CommunicationRule(
                    event_id=ev.id,
                    organization_id=None,
                    channel='in_app',
                    marketing_template_id=None,
                    enabled=False,
                    delay_minutes=0,
                    is_marketing=False,
                    respect_user_prefs=True,
                    priority=10,
                )
            )
            db.session.commit()
            sync_event_rules_to_notification_settings(ev.id)
            db.session.refresh(ns)
            self.assertFalse(ns.enabled)

            r = CommunicationRule.query.filter_by(event_id=ev.id).first()
            r.enabled = True
            db.session.commit()
            sync_event_rules_to_notification_settings(ev.id)
            db.session.refresh(ns)
            self.assertTrue(ns.enabled)

            db.session.delete(r)
            db.session.delete(ev)
            db.session.delete(ns)
            db.session.commit()


if __name__ == '__main__':
    unittest.main()
