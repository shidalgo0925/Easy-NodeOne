#!/usr/bin/env python3
"""Idempotente: permisos academic.* y asignación a roles SA y AD."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

PERMS = (
    ('academic.students.manage', 'Académico estudiantes'),
    ('academic.courses.manage', 'Académico cursos'),
    ('academic.enrollments.manage', 'Académico matrículas'),
)


def main():
    from sqlalchemy import insert, select

    from app import app, db
    from models.associations import role_permission_table
    from models.users import Permission, Role

    with app.app_context():
        for code, name in PERMS:
            if Permission.query.filter_by(code=code).first() is None:
                db.session.add(Permission(code=code, name=name))
        db.session.commit()

        codes = [c for c, _ in PERMS]
        perm_rows = Permission.query.filter(Permission.code.in_(codes)).all()
        perm_ids = {p.code: p.id for p in perm_rows}

        for role_code in ('SA', 'AD'):
            role = Role.query.filter_by(code=role_code).first()
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
            for code, pid in perm_ids.items():
                if pid not in existing:
                    db.session.execute(
                        insert(role_permission_table).values(role_id=role.id, permission_id=pid)
                    )
        db.session.commit()
        print('OK academic permissions')


if __name__ == '__main__':
    main()
