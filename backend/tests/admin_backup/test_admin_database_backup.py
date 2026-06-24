"""Unit tests: servicio admin_database_backup."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from nodeone.services import admin_database_backup as svc


class TestAdminDatabaseBackup(unittest.TestCase):
    def test_is_postgresql_backend(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://u:p@localhost/db'}, clear=False):
            self.assertTrue(svc.is_postgresql_backend())
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///instance/x.db'}, clear=False):
            self.assertFalse(svc.is_postgresql_backend())

    def test_pg_database_name(self):
        self.assertEqual(
            svc.pg_database_name('postgresql://u:p@127.0.0.1:5432/easynodeone_relatic'),
            'easynodeone_relatic',
        )

    def test_is_safe_backup_filename(self):
        self.assertTrue(svc.is_safe_backup_filename('pg_backup_easynodeone_relatic_20260622.dump'))
        self.assertTrue(svc.is_safe_backup_filename('relatic_2026-06-24_02-00.sql'))
        self.assertFalse(svc.is_safe_backup_filename('../etc/passwd'))
        self.assertFalse(svc.is_safe_backup_filename(''))

    def test_list_admin_backups_pg(self):
        with tempfile.TemporaryDirectory() as tmp:
            backups = os.path.join(tmp, 'backups')
            os.makedirs(backups)
            dump = os.path.join(backups, 'pg_backup_test_20260101.dump')
            with open(dump, 'wb') as fh:
                fh.write(b'PGDMP')
            rows = svc.list_admin_backups(tmp)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['engine'], 'postgresql')
            self.assertTrue(rows[0]['deletable'])
            self.assertFalse(rows[0]['restorable'])

    def test_server_backup_pattern_relatic(self):
        with patch.dict(os.environ, {'INSTANCE_NAME': 'relatic'}, clear=False):
            self.assertEqual(svc._server_backup_glob_pattern(), 'relatic_*.sql')

    def test_resolve_server_backup_path_rejects_traversal(self):
        with patch.dict(os.environ, {'INSTANCE_NAME': 'relatic'}, clear=False):
            self.assertIsNone(svc.resolve_server_backup_path('../../../etc/passwd'))

    def test_list_all_backups_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ,
                {'DATABASE_URL': 'postgresql://u:p@localhost/easynodeone_dev', 'INSTANCE_NAME': 'dev'},
                clear=False,
            ):
                admin, server, meta = svc.list_all_backups(tmp)
                self.assertIsInstance(admin, list)
                self.assertIsInstance(server, list)
                self.assertTrue(meta['postgresql'])
                self.assertEqual(meta['database_name'], 'easynodeone_dev')


if __name__ == '__main__':
    unittest.main()
