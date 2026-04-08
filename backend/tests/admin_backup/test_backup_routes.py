"""Smoke: blueprint admin_backup."""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestAdminBackupBlueprint(unittest.TestCase):
    def test_backup_endpoints(self):
        from app import app

        endpoints = {r.endpoint for r in app.url_map.iter_rules()}
        required = {
            'admin_backup.admin_backup',
            'admin_backup.create_backup',
            'admin_backup.download_backup',
            'admin_backup.delete_backup',
            'admin_backup.restore_backup',
        }
        self.assertFalse(required - endpoints, f'Faltan: {sorted(required - endpoints)}')

    def test_backup_paths(self):
        from app import app

        by_ep = {r.endpoint: r.rule for r in app.url_map.iter_rules()}
        self.assertEqual(by_ep.get('admin_backup.admin_backup'), '/admin/backup')


if __name__ == '__main__':
    unittest.main()
