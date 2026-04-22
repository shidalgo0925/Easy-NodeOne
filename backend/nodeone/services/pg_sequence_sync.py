"""Sincroniza secuencias PostgreSQL cuando quedan desalineadas respecto a MAX(id) (importes, restores)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_saas_organization_id_sequence_postgresql(db, engine, printfn=None) -> None:
    """
    Evita: duplicate key value violates unique constraint \"saas_organization_pkey\" Key (id)=(1) already exists
    cuando la secuencia saas_organization_id_seq apunta a 1 pero ya existe fila id=1.
    Solo PostgreSQL; SQLite u otros dialectos no hacen nada.
    """
    if engine.dialect.name != 'postgresql':
        return
    insp = inspect(engine)
    if 'saas_organization' not in insp.get_table_names():
        return
    try:
        seq = db.session.execute(
            text("SELECT pg_get_serial_sequence('saas_organization', 'id')")
        ).scalar()
        if not seq:
            return
        max_id = db.session.execute(
            text('SELECT COALESCE(MAX(id), 0) FROM saas_organization')
        ).scalar()
        max_id = int(max_id or 0)
        nrows = int(
            db.session.execute(text('SELECT COUNT(*) FROM saas_organization')).scalar() or 0
        )
        if nrows == 0:
            # Tabla vacía: el próximo INSERT debe poder usar id=1
            db.session.execute(
                text("SELECT setval(pg_get_serial_sequence('saas_organization', 'id'), 1, false)")
            )
        else:
            # Alinear: próximo id = max(id) + 1
            db.session.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('saas_organization', 'id'), :mx, true)"
                ),
                {'mx': max_id},
            )
        db.session.commit()
        if printfn:
            printfn(f'seq saas_organization.id aligned (max_id={max_id}, rows={nrows})')
    except Exception:
        db.session.rollback()
        raise
