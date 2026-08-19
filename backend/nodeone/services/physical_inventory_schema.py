"""DDL idempotente — toma física (physical_inventory_count)."""

from __future__ import annotations

from sqlalchemy import inspect


def ensure_physical_inventory_schema(db, engine, printfn=None) -> None:
    from models.physical_inventory import PhysicalInventoryCount, PhysicalInventoryCountLine

    try:
        PhysicalInventoryCount.__table__.create(engine, checkfirst=True)
        PhysicalInventoryCountLine.__table__.create(engine, checkfirst=True)
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! physical_inventory_count create: {ex}')
        return
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if 'physical_inventory_count' not in tables or 'physical_inventory_count_line' not in tables:
        if printfn:
            printfn('! physical_inventory_count ausente (¿owner DDL?)')
        return
    if printfn:
        printfn('physical_inventory_count: tablas listas')
