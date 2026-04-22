"""Tests del CommunicationEngine (Fase 1)."""
import sys
import unittest
import uuid
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def _ensure_tables():
    from app import db
    from models.communication_rules import (
        CommunicationEvent,
        CommunicationLog,
        CommunicationRule,
        UserCommunicationPreference,
    )

    CommunicationEvent.__table__.create(db.engine, checkfirst=True)
    CommunicationRule.__table__.create(db.engine, checkfirst=True)
    UserCommunicationPreference.__table__.create(db.engine, checkfirst=True)
    CommunicationLog.__table__.create(db.engine, checkfirst=True)


class TestCommunicationEngine(unittest.TestCase):
    _test_event_code = '__test_comm_engine__'

    @classmethod
    def setUpClass(cls):
        from app import app

        cls.app = app

    def setUp(self):
        self._ctx = self.app.app_context()
        self._ctx.push()
        _ensure_tables()
        from app import db
        from models.communication_rules import (
            CommunicationEvent,
            CommunicationLog,
            CommunicationRule,
            UserCommunicationPreference,
        )
        from models.users import User

        self.db = db
        self.CommunicationEvent = CommunicationEvent
        self.CommunicationLog = CommunicationLog
        self.CommunicationRule = CommunicationRule
        self.UserCommunicationPreference = UserCommunicationPreference
        self.User = User

        suffix = uuid.uuid4().hex[:12]
        self._user = User(
            email=f'comm_test_{suffix}@example.invalid',
            password_hash='x',
            first_name='T',
            last_name='Comm',
            organization_id=1,
        )
        db.session.add(self._user)
        db.session.commit()
        self.user_id = self._user.id

        ev = CommunicationEvent.query.filter_by(code=self._test_event_code).first()
        if not ev:
            ev = CommunicationEvent(
                code=self._test_event_code,
                name='Test event',
                description='unit test',
                category='system',
            )
            db.session.add(ev)
            db.session.commit()
        self.event_id = ev.id

    def tearDown(self):
        from app import db
        from models.communication_rules import (
            CommunicationEvent,
            CommunicationLog,
            CommunicationRule,
            UserCommunicationPreference,
        )

        CommunicationLog.query.filter_by(user_id=self.user_id).delete(synchronize_session=False)
        CommunicationRule.query.filter_by(event_id=self.event_id).delete(synchronize_session=False)
        UserCommunicationPreference.query.filter_by(user_id=self.user_id).delete(synchronize_session=False)
        db.session.delete(self._user)
        db.session.commit()
        # Mantener CommunicationEvent catálogo de test para reutilizar id estable en misma BD
        self._ctx.pop()

    def test_unknown_event_logs_skipped(self):
        from nodeone.modules.communications.services.engine import CommunicationEngine

        r = CommunicationEngine.trigger(
            '__no_such_event_xyz__',
            self.user_id,
            commit=True,
        )
        self.assertEqual(r.actions, [])
        logs = self.CommunicationLog.query.filter_by(user_id=self.user_id).all()
        self.assertTrue(any(x.status == 'skipped_unknown_event' for x in logs))

    def test_no_rules_logs_skipped(self):
        from nodeone.modules.communications.services.engine import CommunicationEngine

        # Quitar reglas para este evento
        self.CommunicationRule.query.filter_by(event_id=self.event_id).delete(synchronize_session=False)
        self.db.session.commit()

        r = CommunicationEngine.trigger(self._test_event_code, self.user_id, commit=True)
        self.assertEqual(r.actions, [])
        logs = self.CommunicationLog.query.filter_by(user_id=self.user_id).all()
        self.assertTrue(any(x.status == 'skipped_no_rules' for x in logs))

    def test_rule_email_no_hook_executed_no_hook(self):
        from nodeone.modules.communications.services.engine import CommunicationEngine

        self.CommunicationRule.query.filter_by(event_id=self.event_id).delete(synchronize_session=False)
        self.db.session.add(
            self.CommunicationRule(
                event_id=self.event_id,
                organization_id=None,
                channel='email',
                enabled=True,
                delay_minutes=0,
                respect_user_prefs=True,
                priority=5,
            )
        )
        self.db.session.commit()

        r = CommunicationEngine.trigger(self._test_event_code, self.user_id, commit=True)
        self.assertEqual(len(r.actions), 1)
        self.assertEqual(r.actions[0].status, 'executed_no_hook')

    def test_user_preference_disables_channel(self):
        from nodeone.modules.communications.services.engine import CommunicationEngine

        self.CommunicationRule.query.filter_by(event_id=self.event_id).delete(synchronize_session=False)
        self.db.session.add(
            self.CommunicationRule(
                event_id=self.event_id,
                organization_id=None,
                channel='email',
                enabled=True,
                delay_minutes=0,
                respect_user_prefs=True,
                priority=5,
            )
        )
        self.db.session.add(
            self.UserCommunicationPreference(
                user_id=self.user_id,
                event_id=self.event_id,
                channel='email',
                enabled=False,
            )
        )
        self.db.session.commit()

        r = CommunicationEngine.trigger(self._test_event_code, self.user_id, commit=True)
        self.assertEqual(len(r.actions), 1)
        self.assertEqual(r.actions[0].status, 'skipped_user_preference')

    def test_email_hook_called(self):
        from nodeone.modules.communications.services.engine import CommunicationEngine, CommunicationHooks

        self.CommunicationRule.query.filter_by(event_id=self.event_id).delete(synchronize_session=False)
        self.db.session.add(
            self.CommunicationRule(
                event_id=self.event_id,
                organization_id=None,
                channel='email',
                enabled=True,
                delay_minutes=0,
                respect_user_prefs=True,
                priority=5,
            )
        )
        self.db.session.commit()

        called = []

        def hook(**kwargs):
            called.append(kwargs)

        hooks = CommunicationHooks(enqueue_email=lambda **kw: hook(**kw))
        r = CommunicationEngine.trigger(
            self._test_event_code,
            self.user_id,
            hooks=hooks,
            commit=True,
        )
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]['user_id'], self.user_id)
        self.assertEqual(len(r.actions), 1)
        self.assertEqual(r.actions[0].status, 'executed')


if __name__ == '__main__':
    unittest.main()
