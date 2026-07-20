"""DDL idempotente — modelo maestro Core (Etapa 10b)."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _exec(engine, ddl: str, printfn, label: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(ddl))
    if printfn:
        printfn(label)


def ensure_core_master_schema(db, engine, printfn=None) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    tables = set(insp.get_table_names())

    if 'core_org_unit' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_org_unit (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                parent_id INTEGER REFERENCES core_org_unit(id) ON DELETE SET NULL,
                unit_ref VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                unit_type VARCHAR(32) NOT NULL DEFAULT 'branch',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_core_org_unit_ref UNIQUE (organization_id, unit_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_core_org_unit_org ON core_org_unit (organization_id);
            CREATE INDEX IF NOT EXISTS ix_core_org_unit_type ON core_org_unit (organization_id, unit_type);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_org_unit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                parent_id INTEGER,
                unit_ref VARCHAR(64) NOT NULL,
                name VARCHAR(200) NOT NULL,
                unit_type VARCHAR(32) NOT NULL DEFAULT 'branch',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                notes TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, unit_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_core_org_unit_org ON core_org_unit (organization_id);
            """
        _exec(engine, ddl, printfn, 'core_org_unit')

    if 'core_address' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_address (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                owner_type VARCHAR(32) NOT NULL,
                owner_id INTEGER NOT NULL,
                kind VARCHAR(32) NOT NULL DEFAULT 'fiscal',
                line1 VARCHAR(300),
                line2 VARCHAR(300),
                city VARCHAR(120),
                state VARCHAR(120),
                postal_code VARCHAR(32),
                country VARCHAR(8),
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_core_address_owner
                ON core_address (organization_id, owner_type, owner_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_address (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                owner_type VARCHAR(32) NOT NULL,
                owner_id INTEGER NOT NULL,
                kind VARCHAR(32) NOT NULL DEFAULT 'fiscal',
                line1 VARCHAR(300),
                line2 VARCHAR(300),
                city VARCHAR(120),
                state VARCHAR(120),
                postal_code VARCHAR(32),
                country VARCHAR(8),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_core_address_owner
                ON core_address (organization_id, owner_type, owner_id);
            """
        _exec(engine, ddl, printfn, 'core_address')

    if 'core_attachment' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_attachment (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                mime_type VARCHAR(128),
                storage_path VARCHAR(500) NOT NULL,
                checksum VARCHAR(128),
                uploaded_by_user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_core_attachment_org ON core_attachment (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_attachment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                mime_type VARCHAR(128),
                storage_path VARCHAR(500) NOT NULL,
                checksum VARCHAR(128),
                uploaded_by_user_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_core_attachment_org ON core_attachment (organization_id);
            """
        _exec(engine, ddl, printfn, 'core_attachment')

    if 'core_product' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_product (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                product_ref VARCHAR(64) NOT NULL,
                name VARCHAR(300) NOT NULL,
                description TEXT,
                product_type VARCHAR(32) NOT NULL DEFAULT 'good',
                tracks_inventory BOOLEAN NOT NULL DEFAULT FALSE,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                unit_price DOUBLE PRECISION NOT NULL DEFAULT 0,
                currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                source_app_id VARCHAR(64),
                barcode VARCHAR(64),
                cost_price DOUBLE PRECISION,
                min_stock DOUBLE PRECISION,
                max_stock DOUBLE PRECISION,
                category VARCHAR(120),
                image_url VARCHAR(500),
                uom VARCHAR(16) DEFAULT 'und',
                purchase_uom VARCHAR(16),
                pack_factor DOUBLE PRECISION DEFAULT 1,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_core_product_ref UNIQUE (organization_id, product_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_core_product_org ON core_product (organization_id);
            CREATE INDEX IF NOT EXISTS ix_core_product_type ON core_product (organization_id, product_type);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                product_ref VARCHAR(64) NOT NULL,
                name VARCHAR(300) NOT NULL,
                description TEXT,
                product_type VARCHAR(32) NOT NULL DEFAULT 'good',
                tracks_inventory BOOLEAN NOT NULL DEFAULT 0,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                unit_price REAL NOT NULL DEFAULT 0,
                currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                source_app_id VARCHAR(64),
                barcode VARCHAR(64),
                cost_price REAL,
                min_stock REAL,
                max_stock REAL,
                category VARCHAR(120),
                image_url VARCHAR(500),
                uom VARCHAR(16) DEFAULT 'und',
                purchase_uom VARCHAR(16),
                pack_factor REAL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, product_ref)
            );
            CREATE INDEX IF NOT EXISTS ix_core_product_org ON core_product (organization_id);
            """
        _exec(engine, ddl, printfn, 'core_product')

    _ensure_core_product_standard_columns(engine, insp, dialect, printfn)

    if 'core_contact_legacy_link' not in tables:
        if dialect == 'postgresql':
            ddl = """
            CREATE TABLE IF NOT EXISTS core_contact_legacy_link (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES saas_organization(id) ON DELETE CASCADE,
                contact_id INTEGER NOT NULL REFERENCES en1_contact(id) ON DELETE CASCADE,
                legacy_contact_id INTEGER NOT NULL,
                link_source VARCHAR(32) NOT NULL DEFAULT 'manual',
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
                CONSTRAINT uq_core_contact_legacy_canonical UNIQUE (organization_id, contact_id),
                CONSTRAINT uq_core_contact_legacy_legacy UNIQUE (organization_id, legacy_contact_id)
            );
            CREATE INDEX IF NOT EXISTS ix_core_contact_legacy_org ON core_contact_legacy_link (organization_id);
            """
        else:
            ddl = """
            CREATE TABLE IF NOT EXISTS core_contact_legacy_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                contact_id INTEGER NOT NULL,
                legacy_contact_id INTEGER NOT NULL,
                link_source VARCHAR(32) NOT NULL DEFAULT 'manual',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, contact_id),
                UNIQUE (organization_id, legacy_contact_id)
            );
            CREATE INDEX IF NOT EXISTS ix_core_contact_legacy_org ON core_contact_legacy_link (organization_id);
            """
        _exec(engine, ddl, printfn, 'core_contact_legacy_link')

    _backfill_contact_legacy_links(db, engine, insp, dialect, printfn)
    _ensure_user_linked_contact(db, engine, insp, dialect, printfn)


def _ensure_core_product_standard_columns(engine, insp, dialect, printfn) -> None:
    """Campos standard POS + inventario (UOM, empaque, stock máx.)."""
    # Re-inspeccionar: la tabla puede haberse creado en este mismo ensure.
    live = inspect(engine)
    tables = set(live.get_table_names())
    if 'core_product' not in tables:
        return
    cols = {c['name'] for c in live.get_columns('core_product')}
    additions: list[tuple[str, str, str]] = [
        ('barcode', 'VARCHAR(64)', 'VARCHAR(64)'),
        ('cost_price', 'DOUBLE PRECISION', 'REAL'),
        ('min_stock', 'DOUBLE PRECISION', 'REAL'),
        ('max_stock', 'DOUBLE PRECISION', 'REAL'),
        ('category', 'VARCHAR(120)', 'VARCHAR(120)'),
        ('fiscal_category', 'VARCHAR(32)', 'VARCHAR(32)'),
        ('image_url', 'VARCHAR(500)', 'VARCHAR(500)'),
        ('uom', 'VARCHAR(16)', 'VARCHAR(16)'),
        ('purchase_uom', 'VARCHAR(16)', 'VARCHAR(16)'),
        ('pack_factor', 'DOUBLE PRECISION', 'REAL'),
    ]
    for name, pg_type, sqlite_type in additions:
        if name in cols:
            continue
        col_type = pg_type if dialect == 'postgresql' else sqlite_type
        if dialect == 'postgresql':
            ddl = f'ALTER TABLE core_product ADD COLUMN IF NOT EXISTS {name} {col_type}'
        else:
            ddl = f'ALTER TABLE core_product ADD COLUMN {name} {col_type}'
        _exec(engine, ddl, printfn, f'core_product.{name}')



def _backfill_contact_legacy_links(db, engine, insp, dialect, printfn) -> None:
    tables = set(insp.get_table_names())
    if 'core_contact_legacy_link' not in tables or 'en1_contact' not in tables or 'tenant_crm_contact' not in tables:
        return
    try:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO core_contact_legacy_link
                        (organization_id, contact_id, legacy_contact_id, link_source)
                    SELECT c.organization_id, c.id, t.id, 'backfill_email'
                    FROM en1_contact c
                    JOIN tenant_crm_contact t
                      ON t.organization_id = c.organization_id
                     AND t.email IS NOT NULL AND length(trim(t.email)) > 0
                     AND c.email IS NOT NULL AND length(trim(c.email)) > 0
                     AND lower(trim(t.email)) = lower(trim(c.email))
                    WHERE NOT EXISTS (
                        SELECT 1 FROM core_contact_legacy_link l
                        WHERE l.organization_id = c.organization_id
                          AND (l.contact_id = c.id OR l.legacy_contact_id = t.id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO core_contact_legacy_link
                        (organization_id, contact_id, legacy_contact_id, link_source)
                    SELECT c.organization_id, c.id, t.id, 'backfill_tax_id'
                    FROM en1_contact c
                    JOIN tenant_crm_contact t
                      ON t.organization_id = c.organization_id
                     AND c.tax_id IS NOT NULL AND length(trim(c.tax_id)) > 0
                     AND t.tax_id IS NOT NULL AND length(trim(t.tax_id)) > 0
                     AND trim(c.tax_id) = trim(t.tax_id)
                     AND coalesce(trim(c.dv), '') = coalesce(trim(t.tax_dv), '')
                    WHERE NOT EXISTS (
                        SELECT 1 FROM core_contact_legacy_link l
                        WHERE l.organization_id = c.organization_id
                          AND (l.contact_id = c.id OR l.legacy_contact_id = t.id)
                    )
                    """
                )
            )
        if printfn:
            printfn('core_contact_legacy_link backfill')
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! core_contact_legacy_link backfill: {ex}')


def _ensure_user_linked_contact(db, engine, insp, dialect, printfn) -> None:
    tables = set(insp.get_table_names())
    if 'user' not in tables or 'en1_contact' not in tables:
        return

    user_tbl = 'user'
    ucols = {c['name'] for c in insp.get_columns(user_tbl)}
    if 'linked_contact_id' not in ucols:
        if dialect == 'postgresql':
            ddl = """
            ALTER TABLE "user"
                ADD COLUMN IF NOT EXISTS linked_contact_id INTEGER
                REFERENCES en1_contact(id) ON DELETE SET NULL;
            CREATE INDEX IF NOT EXISTS ix_user_linked_contact ON "user" (linked_contact_id);
            """
        else:
            ddl = """
            ALTER TABLE user ADD COLUMN linked_contact_id INTEGER REFERENCES en1_contact(id);
            CREATE INDEX IF NOT EXISTS ix_user_linked_contact ON user (linked_contact_id);
            """
        try:
            _exec(engine, ddl, printfn, 'user.linked_contact_id')
        except Exception as ex:
            db.session.rollback()
            if printfn:
                printfn(f'! user.linked_contact_id DDL: {ex}')
            return

    try:
        from sqlalchemy import text

        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE "user" u SET linked_contact_id = (
                        SELECT c.id FROM en1_contact c
                        WHERE c.organization_id = u.organization_id
                          AND c.email IS NOT NULL AND length(trim(c.email)) > 0
                          AND u.email IS NOT NULL AND length(trim(u.email)) > 0
                          AND lower(trim(c.email)) = lower(trim(u.email))
                        ORDER BY c.id ASC LIMIT 1
                    )
                    WHERE u.linked_contact_id IS NULL
                      AND EXISTS (
                          SELECT 1 FROM en1_contact c2
                          WHERE c2.organization_id = u.organization_id
                            AND c2.email IS NOT NULL AND length(trim(c2.email)) > 0
                            AND u.email IS NOT NULL AND length(trim(u.email)) > 0
                            AND lower(trim(c2.email)) = lower(trim(u.email))
                          LIMIT 1
                      )
                    """
                )
            )
        if printfn:
            printfn('user.linked_contact_id backfill')
    except Exception as ex:
        db.session.rollback()
        if printfn:
            printfn(f'! user.linked_contact_id backfill: {ex}')
