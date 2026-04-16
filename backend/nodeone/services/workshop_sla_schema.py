"""DDL idempotente: tablas SLA taller + columnas en workshop_orders."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_workshop_sla_schema(db, engine, printfn=None) -> None:
    """Crea tablas SLA y añade columnas si la BD es antigua."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    names = set(insp.get_table_names())

    def _run(sql: str) -> None:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    if 'workshop_process_stage_config' not in names:
        _run(
            """
            CREATE TABLE workshop_process_stage_config (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                stage_key VARCHAR(32) NOT NULL,
                stage_name VARCHAR(120) NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                expected_duration_minutes INTEGER NOT NULL DEFAULT 30,
                color VARCHAR(40) NOT NULL DEFAULT '#0d6efd',
                active BOOLEAN NOT NULL DEFAULT 1,
                service_type_tag VARCHAR(80),
                allow_skip BOOLEAN NOT NULL DEFAULT 0,
                CONSTRAINT uq_workshop_proc_stage_org_key UNIQUE (organization_id, stage_key)
            )
            """
            if dialect == 'sqlite'
            else """
            CREATE TABLE workshop_process_stage_config (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                stage_key VARCHAR(32) NOT NULL,
                stage_name VARCHAR(120) NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                expected_duration_minutes INTEGER NOT NULL DEFAULT 30,
                color VARCHAR(40) NOT NULL DEFAULT '#0d6efd',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                service_type_tag VARCHAR(80),
                allow_skip BOOLEAN NOT NULL DEFAULT FALSE,
                CONSTRAINT uq_workshop_proc_stage_org_key UNIQUE (organization_id, stage_key)
            )
            """
        )
        if printfn:
            printfn('+ tabla workshop_process_stage_config')

    if 'workshop_service_process_config' not in names:
        _run(
            """
            CREATE TABLE workshop_service_process_config (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                service_id INTEGER NOT NULL REFERENCES service(id) ON DELETE CASCADE,
                stage_key VARCHAR(32) NOT NULL,
                expected_duration_minutes INTEGER NOT NULL DEFAULT 30,
                CONSTRAINT uq_workshop_svc_proc_org_svc_stage UNIQUE (organization_id, service_id, stage_key)
            )
            """
            if dialect == 'sqlite'
            else """
            CREATE TABLE workshop_service_process_config (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                service_id INTEGER NOT NULL REFERENCES service(id) ON DELETE CASCADE,
                stage_key VARCHAR(32) NOT NULL,
                expected_duration_minutes INTEGER NOT NULL DEFAULT 30,
                CONSTRAINT uq_workshop_svc_proc_org_svc_stage UNIQUE (organization_id, service_id, stage_key)
            )
            """
        )
        if printfn:
            printfn('+ tabla workshop_service_process_config')

    if 'workshop_order_process_log' not in names:
        _run(
            """
            CREATE TABLE workshop_order_process_log (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES workshop_orders(id) ON DELETE CASCADE,
                stage_key VARCHAR(32) NOT NULL,
                started_at DATETIME NOT NULL,
                ended_at DATETIME,
                duration_minutes FLOAT,
                expected_minutes FLOAT,
                is_delayed BOOLEAN NOT NULL DEFAULT 0,
                delay_minutes FLOAT
            )
            """
            if dialect == 'sqlite'
            else """
            CREATE TABLE workshop_order_process_log (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES workshop_orders(id) ON DELETE CASCADE,
                stage_key VARCHAR(32) NOT NULL,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                duration_minutes DOUBLE PRECISION,
                expected_minutes DOUBLE PRECISION,
                is_delayed BOOLEAN NOT NULL DEFAULT FALSE,
                delay_minutes DOUBLE PRECISION
            )
            """
        )
        if printfn:
            printfn('+ tabla workshop_order_process_log')

    if 'workshop_orders' not in names:
        return
    cols = {c['name'] for c in insp.get_columns('workshop_orders')}
    dt = 'TIMESTAMP' if dialect == 'postgresql' else 'DATETIME'
    paused_def = (
        'sla_paused BOOLEAN NOT NULL DEFAULT 0'
        if dialect == 'sqlite'
        else 'sla_paused BOOLEAN NOT NULL DEFAULT FALSE'
    )
    # (SQL IF NOT EXISTS, ADD COLUMN clásico sin IF NOT EXISTS — fallback SQLite < 3.35)
    planned: list[tuple[str, str]] = []
    if 'sla_stage_started_at' not in cols:
        planned.append(
            (
                f'ALTER TABLE workshop_orders ADD COLUMN IF NOT EXISTS sla_stage_started_at {dt}',
                f'sla_stage_started_at {dt}',
            )
        )
    if 'sla_expected_minutes' not in cols:
        planned.append(
            (
                'ALTER TABLE workshop_orders ADD COLUMN IF NOT EXISTS sla_expected_minutes INTEGER',
                'sla_expected_minutes INTEGER',
            )
        )
    if 'sla_paused' not in cols:
        planned.append(
            (
                f'ALTER TABLE workshop_orders ADD COLUMN IF NOT EXISTS {paused_def}',
                paused_def,
            )
        )
    if 'sla_paused_at' not in cols:
        planned.append(
            (
                f'ALTER TABLE workshop_orders ADD COLUMN IF NOT EXISTS sla_paused_at {dt}',
                f'sla_paused_at {dt}',
            )
        )

    for sql_if, coldef_fb in planned:
        try:
            db.session.execute(text(sql_if))
            db.session.commit()
            if printfn:
                printfn(f'+ workshop_orders.{coldef_fb.split()[0]}')
        except Exception:
            db.session.rollback()
            try:
                insp_cols = {c['name'] for c in inspect(engine).get_columns('workshop_orders')}
                name = coldef_fb.split()[0]
                if name not in insp_cols:
                    db.session.execute(text(f'ALTER TABLE workshop_orders ADD COLUMN {coldef_fb}'))
                    db.session.commit()
                    if printfn:
                        printfn(f'+ workshop_orders.{name} (fallback ADD COLUMN)')
            except Exception:
                db.session.rollback()

    # Datos existentes: iniciar reloj SLA desde fecha de entrada si sigue vacío
    try:
        db.session.execute(
            text(
                'UPDATE workshop_orders SET sla_stage_started_at = entry_date '
                'WHERE sla_stage_started_at IS NULL AND entry_date IS NOT NULL AND status != :st'
            ),
            {'st': 'cancelled'},
        )
        db.session.commit()
        if printfn:
            printfn('* workshop_orders: backfill sla_stage_started_at desde entry_date')
    except Exception:
        db.session.rollback()
