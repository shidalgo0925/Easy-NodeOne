#!/usr/bin/env python3
"""Auditoría de preparación infra IIUS: rutas, Git, runtime, entornos futuros."""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

IIUS_RUNTIME_ROOT = '/opt/easynodeone'
FUTURE_IIUS_ROOTS = ('/opt/iius/dev/app', '/opt/iius/staging/app', '/opt/iius/prod/app')
FORBIDDEN_EDIT = '/var/www/nodeone'


def _run(cmd: list[str], cwd: str | None = None) -> str:
    try:
        return subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT, text=True).strip()
    except Exception as e:
        return f'(error: {e})'


def main() -> int:
    issues: list[str] = []
    notes: list[str] = []

    print('=== IIUS infra readiness ===\n')

    print('## Rutas')
    print(f'  runtime activo: {IIUS_RUNTIME_ROOT}/app')
    print(f'  backend CWD:    {IIUS_RUNTIME_ROOT}/app/backend')
    iius_readme = os.path.isfile('/opt/iius/README.md')
    print(f'  /opt/iius/README.md: {"sí" if iius_readme else "no"}')
    for p in FUTURE_IIUS_ROOTS:
        exists = os.path.isdir(p)
        print(f'  silo {p}: {"esqueleto OK" if exists else "pendiente"}')
        if not exists and not iius_readme:
            notes.append(f'{p} pendiente de aprovisionar')

    if os.path.isdir(FORBIDDEN_EDIT):
        notes.append(f'{FORBIDDEN_EDIT} existe (no es runtime IIUS; no editar para deploy)')

    print('\n## Git (repo app)')
    repo = os.path.join(IIUS_RUNTIME_ROOT, 'app')
    branch = _run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo)
    head = _run(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo)
    dirty = _run(['git', 'status', '--porcelain'], cwd=repo)
    print(f'  rama: {branch}')
    print(f'  HEAD: {head}')
    if branch != 'iius-product':
        issues.append(f'rama activa {branch} != iius-product')
    if dirty:
        issues.append(f'working tree sucio ({len(dirty.splitlines())} líneas)')
        print('  dirty: sí')
    else:
        print('  dirty: no')

    tags = _run(['git', 'tag', '-l', 'iius-*'], cwd=repo)
    print('  tags iius:', tags.replace('\n', ', ') if tags else '(ninguno)')

    print('\n## systemd nodeone.service')
    print(' ', _run(['systemctl', 'show', 'nodeone.service', '-p', 'WorkingDirectory,EnvironmentFile,ActiveState']))

    print('\n## Entorno (.env claves, sin valores)')
    env_path = os.path.join(IIUS_RUNTIME_ROOT, 'app', '.env')
    keys_of_interest = (
        'NODEONE_BRAND_PRESET',
        'REQUIRE_PAID_ACCESS',
        'DATABASE_URL',
        'SQLALCHEMY_DATABASE_URI',
        'BASE_URL',
        'DEFAULT_ORGANIZATION_ID',
    )
    if os.path.isfile(env_path):
        with open(env_path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                if k in keys_of_interest:
                    masked = '(set)' if v.strip() else '(vacío)'
                    if 'postgres' in v.lower():
                        masked = 'postgres'
                    elif 'sqlite' in v.lower():
                        masked = 'sqlite'
                    print(f'  {k}={masked}')
                    if k in ('DATABASE_URL', 'SQLALCHEMY_DATABASE_URI') and 'postgres' in v.lower():
                        notes.append('DATABASE_URL apunta a Postgres (verificar migración)')
    else:
        issues.append('.env no encontrado')

    print('\n## BD aplicación')
    from app import app, db
    from models.saas import SaasOrganization

    with app.app_context():
        uri = str(db.engine.url)
        print(f'  engine: {uri.split("@")[-1] if "@" in uri else uri}')
        if 'sqlite' in uri:
            notes.append('SQLite en producción IIUS — planificar Postgres + backups')
        org = SaasOrganization.query.get(1)
        if org:
            print(f'  org1: {org.name} policy={getattr(org, "registration_policy", None)}')

    print('\n## Smoke scripts disponibles')
    scripts_dir = os.path.join(repo, 'backend', 'scripts')
    for name in sorted(os.listdir(scripts_dir)):
        if name.startswith(('smoke_iius', 'audit_iius', 'test_academic', 'test_iius')):
            print(f'  - {name}')

    if notes:
        print('\n## Notas')
        for n in notes:
            print(f'  - {n}')

    if issues:
        print('\n## ISSUES')
        for i in issues:
            print(f'  - {i}')
        return 1

    print('\nResumen: listo para operar en silo único; separación /opt/iius/* aún no aprovisionada.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
