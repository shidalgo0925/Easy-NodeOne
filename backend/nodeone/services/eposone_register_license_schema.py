"""DDL — licencia comercial por Caja + códigos de activación (no provisioning)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_eposone_register_license_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    if 'eposone_register_license' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_register_license (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                register_ref VARCHAR(64) NOT NULL,
                license_type VARCHAR(32) NOT NULL DEFAULT 'unlicensed',
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                plan_code VARCHAR(64) NOT NULL DEFAULT 'eposone',
                starts_at TIMESTAMP WITHOUT TIME ZONE,
                expires_at TIMESTAMP WITHOUT TIME ZONE,
                trial_used BOOLEAN NOT NULL DEFAULT FALSE,
                trial_started_at TIMESTAMP WITHOUT TIME ZONE,
                trial_expires_at TIMESTAMP WITHOUT TIME ZONE,
                notes VARCHAR(500),
                reason VARCHAR(200),
                activated_by_user_id INTEGER,
                last_validated_at TIMESTAMP WITHOUT TIME ZONE,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_eposone_register_license UNIQUE (organization_id, register_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_reg_lic_org ON eposone_register_license (organization_id);
            CREATE INDEX IF NOT EXISTS ix_eposone_reg_lic_org_reg
                ON eposone_register_license (organization_id, register_ref);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS eposone_register_license (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                register_ref VARCHAR(64) NOT NULL,
                license_type VARCHAR(32) NOT NULL DEFAULT 'unlicensed',
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                plan_code VARCHAR(64) NOT NULL DEFAULT 'eposone',
                starts_at DATETIME,
                expires_at DATETIME,
                trial_used BOOLEAN NOT NULL DEFAULT 0,
                trial_started_at DATETIME,
                trial_expires_at DATETIME,
                notes VARCHAR(500),
                reason VARCHAR(200),
                activated_by_user_id INTEGER,
                last_validated_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, register_ref)
            );
            """
        with engine.begin() as conn:
            for stmt in ddl.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('eposone_register_license: tabla creada')

    if 'eposone_commercial_code' not in insp.get_table_names():
        if dialect == 'postgresql':
            ddl2 = """
            CREATE TABLE IF NOT EXISTS eposone_commercial_code (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER REFERENCES saas_organization(id) ON DELETE CASCADE,
                code VARCHAR(64) NOT NULL UNIQUE,
                benefit_type VARCHAR(32) NOT NULL DEFAULT 'trial',
                duration_days INTEGER,
                max_uses INTEGER NOT NULL DEFAULT 1,
                uses_count INTEGER NOT NULL DEFAULT 0,
                registers_granted INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                expires_at TIMESTAMP WITHOUT TIME ZONE,
                label VARCHAR(200),
                notes VARCHAR(500),
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_eposone_comm_code ON eposone_commercial_code (code);
            """
        else:
            ddl2 = """
            CREATE TABLE IF NOT EXISTS eposone_commercial_code (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER,
                code VARCHAR(64) NOT NULL UNIQUE,
                benefit_type VARCHAR(32) NOT NULL DEFAULT 'trial',
                duration_days INTEGER,
                max_uses INTEGER NOT NULL DEFAULT 1,
                uses_count INTEGER NOT NULL DEFAULT 0,
                registers_granted INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                expires_at DATETIME,
                label VARCHAR(200),
                notes VARCHAR(500),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        with engine.begin() as conn:
            for stmt in ddl2.strip().split(';'):
                s = stmt.strip()
                if s:
                    conn.execute(text(s))
        if printfn:
            printfn('eposone_commercial_code: tabla creada')

    # Provisioning: TTL + estado used
    if 'eposone_provisioning_code' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('eposone_provisioning_code')}
        with engine.begin() as conn:
            if 'expires_at' not in cols:
                if dialect == 'postgresql':
                    conn.execute(
                        text(
                            'ALTER TABLE eposone_provisioning_code '
                            'ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITHOUT TIME ZONE'
                        )
                    )
                else:
                    conn.execute(text('ALTER TABLE eposone_provisioning_code ADD COLUMN expires_at DATETIME'))
                if printfn:
                    printfn('eposone_provisioning_code: columna expires_at')

    # Settings comerciales
    if 'eposone_settings' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('eposone_settings')}
        alters = []
        if 'trial_days_default' not in cols:
            alters.append('trial_days_default INTEGER NOT NULL DEFAULT 15')
        if 'trial_start_policy' not in cols:
            alters.append("trial_start_policy VARCHAR(40) NOT NULL DEFAULT 'on_first_provision'")
        if 'provisioning_code_ttl_minutes' not in cols:
            alters.append('provisioning_code_ttl_minutes INTEGER NOT NULL DEFAULT 30')
        if 'offline_grace_days' not in cols:
            alters.append('offline_grace_days INTEGER NOT NULL DEFAULT 7')
        with engine.begin() as conn:
            for col_def in alters:
                col_name = col_def.split()[0]
                if dialect == 'postgresql':
                    conn.execute(text(f'ALTER TABLE eposone_settings ADD COLUMN IF NOT EXISTS {col_def}'))
                else:
                    try:
                        conn.execute(text(f'ALTER TABLE eposone_settings ADD COLUMN {col_def}'))
                    except Exception:
                        pass
                if printfn:
                    printfn(f'eposone_settings: columna {col_name}')

    # License Engine V1 — columnas extra en eposone_register_license
    if 'eposone_register_license' in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns('eposone_register_license')}
        v1_alters: list[tuple[str, str]] = []
        if 'activation_method' not in cols:
            v1_alters.append(
                ('activation_method', "activation_method VARCHAR(32) NOT NULL DEFAULT 'EN1'")
            )
        if 'grace_until' not in cols:
            v1_alters.append(('grace_until', 'grace_until TIMESTAMP WITHOUT TIME ZONE'))
        if 'issued_at' not in cols:
            v1_alters.append(('issued_at', 'issued_at TIMESTAMP WITHOUT TIME ZONE'))
        if 'features_json' not in cols:
            v1_alters.append(('features_json', 'features_json TEXT'))
        if 'limits_json' not in cols:
            v1_alters.append(('limits_json', 'limits_json TEXT'))
        if v1_alters:
            with engine.begin() as conn:
                for col_name, col_def in v1_alters:
                    if dialect == 'postgresql':
                        conn.execute(
                            text(
                                f'ALTER TABLE eposone_register_license '
                                f'ADD COLUMN IF NOT EXISTS {col_def}'
                            )
                        )
                    else:
                        try:
                            conn.execute(
                                text(f'ALTER TABLE eposone_register_license ADD COLUMN {col_def}')
                            )
                        except Exception:
                            pass
                    if printfn:
                        printfn(f'eposone_register_license: columna {col_name}')
