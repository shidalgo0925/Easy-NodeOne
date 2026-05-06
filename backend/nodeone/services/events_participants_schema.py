"""DDL idempotente: event_participant / event_certificate alineados a import + certificados."""

from __future__ import annotations

from sqlalchemy import inspect, text


def ensure_events_participants_certificates_schema(db, engine, printfn=None) -> None:
    from models.events import EventCertificate, EventParticipant

    EventParticipant.__table__.create(engine, checkfirst=True)
    EventCertificate.__table__.create(engine, checkfirst=True)
    insp = inspect(engine)
    dialect = engine.dialect.name

    def _cols(table: str) -> set[str]:
        if table not in insp.get_table_names():
            return set()
        return {c['name'] for c in insp.get_columns(table)}

    def _run(sql: str) -> bool:
        try:
            db.session.execute(text(sql))
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            if printfn:
                printfn(f'⚠️ DDL omitida o fallida (events schema): {e}')
            return False

    ep = 'event_participant'
    ec = 'event_certificate'

    if ep in insp.get_table_names():
        cols = _cols(ep)
        alters = []
        if 'first_name' not in cols:
            alters.append('ADD COLUMN first_name VARCHAR(120)')
        if 'middle_name' not in cols:
            alters.append('ADD COLUMN middle_name VARCHAR(120)')
        if 'last_name' not in cols:
            alters.append('ADD COLUMN last_name VARCHAR(120)')
        if 'second_last_name' not in cols:
            alters.append('ADD COLUMN second_last_name VARCHAR(120)')
        if 'full_name' not in cols:
            alters.append('ADD COLUMN full_name VARCHAR(255)')
        if 'document_id' not in cols:
            alters.append('ADD COLUMN document_id VARCHAR(80)')
        if 'email' not in cols:
            alters.append('ADD COLUMN email VARCHAR(255)')
        if 'phone' not in cols:
            alters.append('ADD COLUMN phone VARCHAR(50)')
        if 'participant_type' not in cols:
            alters.append("ADD COLUMN participant_type VARCHAR(50) DEFAULT 'external'")
        if 'registration_source' not in cols:
            alters.append("ADD COLUMN registration_source VARCHAR(50) DEFAULT 'admin_manual'")
        if 'attendance_status' not in cols:
            alters.append("ADD COLUMN attendance_status VARCHAR(50) DEFAULT 'pending'")
        if 'certificate_status' not in cols:
            alters.append("ADD COLUMN certificate_status VARCHAR(50) DEFAULT 'pending'")
        if 'checked_in_by' not in cols:
            alters.append('ADD COLUMN checked_in_by INTEGER')
        if 'checked_in_at' not in cols:
            alters.append('ADD COLUMN checked_in_at TIMESTAMP')
        for a in alters:
            _run(f'ALTER TABLE {ep} {a}')

        # user_id nullable (externos)
        if dialect == 'postgresql':
            _run(f'ALTER TABLE {ep} ALTER COLUMN user_id DROP NOT NULL')
            _run(f'ALTER TABLE {ep} ALTER COLUMN participation_category DROP NOT NULL')
            _run(f'ALTER TABLE {ep} DROP CONSTRAINT IF EXISTS uq_event_user')

    insp = inspect(engine)
    if ec in insp.get_table_names():
        cols = {c['name'] for c in insp.get_columns(ec)}
        alters = []
        if 'verification_token' not in cols:
            alters.append('ADD COLUMN verification_token VARCHAR(120)')
        if 'certificate_type' not in cols:
            alters.append("ADD COLUMN certificate_type VARCHAR(50) DEFAULT 'participation'")
        if 'title' not in cols:
            alters.append('ADD COLUMN title VARCHAR(255)')
        if 'expires_at' not in cols:
            alters.append('ADD COLUMN expires_at TIMESTAMP')
        if 'qr_path' not in cols:
            alters.append('ADD COLUMN qr_path VARCHAR(500)')
        if 'status' not in cols:
            alters.append("ADD COLUMN status VARCHAR(50) DEFAULT 'generated'")
        if 'revoked_reason' not in cols:
            alters.append('ADD COLUMN revoked_reason TEXT')
        if 'revoked_at' not in cols:
            alters.append('ADD COLUMN revoked_at TIMESTAMP')
        if 'revoked_by' not in cols:
            alters.append('ADD COLUMN revoked_by INTEGER')
        for a in alters:
            _run(f'ALTER TABLE {ec} {a}')

        insp = inspect(engine)
        cols_ec = _cols(ec)
        if dialect == 'postgresql' and 'verification_token' in cols_ec:
            _run(
                f'CREATE UNIQUE INDEX IF NOT EXISTS uq_event_certificate_verification_token '
                f'ON {ec} (verification_token) WHERE verification_token IS NOT NULL'
            )

    if printfn:
        printfn('ensure events participants/certificates schema')
