"""Respaldos de BD desde el panel admin (PostgreSQL o SQLite legacy)."""

from __future__ import annotations

import glob
import os
import re
import subprocess
from datetime import datetime
from urllib.parse import urlparse

_SAFE_FILENAME = re.compile(r'^[a-zA-Z0-9._-]+$')


def database_url() -> str:
    return (os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI') or '').strip()


def is_postgresql_backend() -> bool:
    url = database_url().lower()
    return url.startswith('postgresql://') or url.startswith('postgres://')


def pg_database_name(url: str | None = None) -> str:
    parsed = urlparse(url or database_url())
    name = (parsed.path or '').lstrip('/')
    return name or 'database'


def admin_backups_dir(project_root: str) -> str:
    path = os.path.join(project_root, 'backups')
    os.makedirs(path, exist_ok=True)
    return path


def server_backups_dir() -> str:
    return (
        os.environ.get('EASYNODEONE_SERVER_BACKUP_DIR', '/opt/easynodeone/backups').strip()
        or '/opt/easynodeone/backups'
    )


def _server_backup_glob_pattern() -> str | None:
    instance = (os.environ.get('INSTANCE_NAME') or '').strip().lower()
    if instance == 'relatic':
        return 'relatic_*.sql'
    if instance == 'prod':
        return 'prod_*.sql'
    if instance == 'staging':
        return 'staging_*.sql'
    if instance == 'dev':
        return 'dev_*.sql'
    return None


def is_safe_backup_filename(filename: str) -> bool:
    return bool(filename and _SAFE_FILENAME.match(filename))


def _file_entry(filename: str, filepath: str, *, source: str, deletable: bool, engine: str) -> dict:
    st = os.stat(filepath)
    return {
        'filename': filename,
        'size': st.st_size,
        'size_mb': round(st.st_size / (1024 * 1024), 2),
        'created_at': datetime.fromtimestamp(st.st_mtime),
        'path': filepath,
        'source': source,
        'deletable': deletable,
        'engine': engine,
        'restorable': engine == 'sqlite',
    }


def list_admin_backups(project_root: str) -> list[dict]:
    backups_dir = admin_backups_dir(project_root)
    rows: list[dict] = []
    if not os.path.isdir(backups_dir):
        return rows
    for filename in os.listdir(backups_dir):
        if filename.startswith('nodeone_backup_') and filename.endswith('.db'):
            rows.append(
                _file_entry(
                    filename,
                    os.path.join(backups_dir, filename),
                    source='admin',
                    deletable=True,
                    engine='sqlite',
                )
            )
        elif filename.startswith('pg_backup_') and (
            filename.endswith('.dump') or filename.endswith('.sql')
        ):
            rows.append(
                _file_entry(
                    filename,
                    os.path.join(backups_dir, filename),
                    source='admin',
                    deletable=True,
                    engine='postgresql',
                )
            )
    rows.sort(key=lambda r: r['created_at'], reverse=True)
    return rows


def list_server_backups() -> list[dict]:
    pattern = _server_backup_glob_pattern()
    if not pattern:
        return []
    root = server_backups_dir()
    if not os.path.isdir(root):
        return []
    rows: list[dict] = []
    for filepath in sorted(glob.glob(os.path.join(root, pattern)), reverse=True):
        filename = os.path.basename(filepath)
        if not is_safe_backup_filename(filename):
            continue
        rows.append(
            _file_entry(
                filename,
                filepath,
                source='server',
                deletable=False,
                engine='postgresql',
            )
        )
    return rows


def list_all_backups(project_root: str) -> tuple[list[dict], list[dict], dict]:
    admin = list_admin_backups(project_root)
    server = list_server_backups()
    meta = {
        'engine': 'postgresql' if is_postgresql_backend() else 'sqlite',
        'database_name': pg_database_name() if is_postgresql_backend() else 'membership_legacy.db',
        'postgresql': is_postgresql_backend(),
    }
    return admin, server, meta


def sqlite_db_path(project_root: str) -> str:
    return os.path.join(project_root, 'instance', 'membership_legacy.db')


def create_sqlite_backup(project_root: str) -> tuple[str, str]:
    import shutil

    db_path = sqlite_db_path(project_root)
    if not os.path.exists(db_path):
        raise FileNotFoundError('Base de datos SQLite no encontrada')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'nodeone_backup_{timestamp}.db'
    backup_path = os.path.join(admin_backups_dir(project_root), filename)
    shutil.copy2(db_path, backup_path)
    return backup_path, filename


def create_postgresql_backup(project_root: str) -> tuple[str, str]:
    url = database_url()
    if not url:
        raise RuntimeError('DATABASE_URL no configurada para este silo')
    dbname = pg_database_name(url)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'pg_backup_{dbname}_{timestamp}.dump'
    backup_path = os.path.join(admin_backups_dir(project_root), filename)
    proc = subprocess.run(
        ['pg_dump', url, '-Fc', '-f', backup_path],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or 'pg_dump falló').strip()
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
        raise RuntimeError(err[:500])
    if not os.path.isfile(backup_path) or os.path.getsize(backup_path) < 1:
        raise RuntimeError('pg_dump no generó un archivo válido')
    return backup_path, filename


def resolve_admin_backup_path(project_root: str, filename: str) -> str | None:
    if not is_safe_backup_filename(filename):
        return None
    path = os.path.join(admin_backups_dir(project_root), filename)
    if not os.path.isfile(path):
        return None
    if filename.startswith('nodeone_backup_') and filename.endswith('.db'):
        return path
    if filename.startswith('pg_backup_') and (
        filename.endswith('.dump') or filename.endswith('.sql')
    ):
        return path
    return None


def resolve_server_backup_path(filename: str) -> str | None:
    if not is_safe_backup_filename(filename):
        return None
    pattern = _server_backup_glob_pattern()
    if not pattern:
        return None
    prefix = pattern.split('*', 1)[0]
    if not filename.startswith(prefix):
        return None
    path = os.path.join(server_backups_dir(), filename)
    if not os.path.isfile(path):
        return None
    return path


def mimetype_for_filename(filename: str) -> str:
    if filename.endswith('.db'):
        return 'application/x-sqlite3'
    if filename.endswith('.dump'):
        return 'application/octet-stream'
    if filename.endswith('.sql'):
        return 'application/sql'
    return 'application/octet-stream'
