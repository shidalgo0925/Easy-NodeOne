-- Ejecutar como SUPERUSER o como OWNER de las tablas (ej. el rol que creó el schema).
-- El usuario de la app suele no tener privilegio ALTER → bootstrap Python no puede añadir columnas.
-- Uso típico: psql "$DATABASE_URL" -f 002_event_participant_certificate_en1_pg.sql

-- event_participant (columnas del modelo EN1 que pueden faltar en instalaciones antiguas)
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS first_name VARCHAR(120);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS middle_name VARCHAR(120);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS last_name VARCHAR(120);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS second_last_name VARCHAR(120);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS document_id VARCHAR(80);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS participant_type VARCHAR(50) DEFAULT 'external';
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS registration_source VARCHAR(50) DEFAULT 'admin_manual';
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMP;
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS checked_in_by INTEGER;
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS attendance_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE event_participant ADD COLUMN IF NOT EXISTS certificate_status VARCHAR(50) DEFAULT 'pending';

ALTER TABLE event_participant ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE event_participant ALTER COLUMN participation_category DROP NOT NULL;
ALTER TABLE event_participant DROP CONSTRAINT IF EXISTS uq_event_user;

-- event_certificate
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS verification_token VARCHAR(120);
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS certificate_type VARCHAR(50) DEFAULT 'participation';
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS title VARCHAR(255);
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS qr_path VARCHAR(500);
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'generated';
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS revoked_reason TEXT;
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP;
ALTER TABLE event_certificate ADD COLUMN IF NOT EXISTS revoked_by INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS uq_event_certificate_verification_token
  ON event_certificate (verification_token)
  WHERE verification_token IS NOT NULL;
