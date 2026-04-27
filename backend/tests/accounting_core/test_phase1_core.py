import sys
import unittest
from datetime import date
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAccountingCorePhase1(unittest.TestCase):
    def setUp(self):
        from app import app, db, default_organization_id
        from models.accounting_core import Account, Journal, JournalEntry, JournalItem
        from nodeone.modules.accounting_core.service import ensure_accounting_core_schema

        self.app = app
        self.db = db
        self.default_organization_id = int(default_organization_id())
        with self.app.app_context():
            ensure_accounting_core_schema()
            # Limpieza de datos de prueba de esta clase
            JournalItem.query.delete()
            JournalEntry.query.delete()
            Journal.query.filter(Journal.code.like('T%')).delete(synchronize_session=False)
            Account.query.filter(Account.code.like('T%')).delete(synchronize_session=False)
            self.db.session.commit()

    def test_account_and_journal_and_post_reverse_flow(self):
        from models.accounting_core import JournalEntry
        from nodeone.modules.accounting_core import service

        with self.app.app_context():
            cash = service.create_account(
                self.default_organization_id,
                {'code': 'T100', 'name': 'Test Caja', 'type': 'asset', 'is_active': True},
            )
            income = service.create_account(
                self.default_organization_id,
                {'code': 'T400', 'name': 'Test Ingreso', 'type': 'income', 'is_active': True},
            )
            journal = service.create_journal(
                self.default_organization_id,
                {'code': 'TGEN', 'name': 'Test Diario', 'type': 'general', 'default_account_id': cash.id},
            )
            entry = service.create_entry_draft(
                self.default_organization_id,
                journal.id,
                {
                    'date': date.today().isoformat(),
                    'reference': 'ASIENTO TEST',
                    'lines': [
                        {'account_id': cash.id, 'debit': '100.00', 'credit': '0'},
                        {'account_id': income.id, 'debit': '0', 'credit': '100.00'},
                    ],
                },
            )
            self.assertEqual(entry.state, 'draft')
            posted = service.post_entry(entry, user_id=None)
            self.assertEqual(posted.state, 'posted')
            rev = service.reverse_entry(posted, user_id=None)
            original = JournalEntry.query.get(posted.id)
            self.assertEqual(original.state, 'reversed')
            self.assertEqual(original.reversed_by_entry_id, rev.id)
            self.assertEqual(rev.state, 'posted')

    def test_post_rejects_unbalanced(self):
        from nodeone.modules.accounting_core import service

        with self.app.app_context():
            a1 = service.create_account(
                self.default_organization_id,
                {'code': 'T110', 'name': 'Activo Test', 'type': 'asset', 'is_active': True},
            )
            a2 = service.create_account(
                self.default_organization_id,
                {'code': 'T410', 'name': 'Ingreso Test', 'type': 'income', 'is_active': True},
            )
            j = service.create_journal(
                self.default_organization_id,
                {'code': 'TBNK', 'name': 'Banco Test', 'type': 'bank', 'default_account_id': a1.id},
            )
            e = service.create_entry_draft(
                self.default_organization_id,
                j.id,
                {
                    'date': date.today().isoformat(),
                    'reference': 'DESBALANCE',
                    'lines': [
                        {'account_id': a1.id, 'debit': '80.00', 'credit': '0'},
                        {'account_id': a2.id, 'debit': '0', 'credit': '60.00'},
                    ],
                },
            )
            with self.assertRaises(ValueError):
                service.post_entry(e, user_id=None)


if __name__ == '__main__':
    unittest.main()
