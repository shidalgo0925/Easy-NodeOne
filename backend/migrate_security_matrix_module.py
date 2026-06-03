#!/usr/bin/env python3
"""Tablas security_matrix_manager + permiso security_matrix.admin + catálogo SaaS."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import insert, select

from app import app, db  # noqa: E402
from nodeone.services.saas_catalog_defaults import (  # noqa: E402
    ensure_saas_module_catalog,
    ensure_toggleable_tenant_module_links,
)
from models.security_matrix import (  # noqa: E402
    SecurityMatrixCatalogSnapshot,
    SecurityMatrixChangePreview,
    SecurityMatrixImport,
    SecurityMatrixRow,
)
from models.users import Permission, Role, role_permission_table  # noqa: E402

PERM_CODE = 'security_matrix.admin'
PERM_NAME = 'Matriz de permisos Odoo (admin)'
ROLE_CODES = ('SA', 'AD')


def main():
    with app.app_context():
        for model in (
            SecurityMatrixCatalogSnapshot,
            SecurityMatrixImport,
            SecurityMatrixRow,
            SecurityMatrixChangePreview,
        ):
            model.__table__.create(db.engine, checkfirst=True)
            print(f'✅ Tabla {model.__tablename__}')

        p = Permission.query.filter_by(code=PERM_CODE).first()
        if p is None:
            p = Permission(code=PERM_CODE, name=PERM_NAME)
            db.session.add(p)
            db.session.commit()
            print(f'✅ Permiso {PERM_CODE}')
        pid = p.id

        for rcode in ROLE_CODES:
            role = Role.query.filter_by(code=rcode).first()
            if not role:
                continue
            existing = {
                row[0]
                for row in db.session.execute(
                    select(role_permission_table.c.permission_id).where(
                        role_permission_table.c.role_id == role.id
                    )
                )
            }
            if pid not in existing:
                db.session.execute(
                    insert(role_permission_table).values(role_id=role.id, permission_id=pid)
                )
                print(f'📋 Rol {rcode}: {PERM_CODE}')
        db.session.commit()
        ensure_saas_module_catalog(printfn=print)
        ensure_toggleable_tenant_module_links(printfn=print)
        print('Listo (tablas, permiso, saas_module security_matrix).')


if __name__ == '__main__':
    main()
