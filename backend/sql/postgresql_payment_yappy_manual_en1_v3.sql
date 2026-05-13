-- Patch PostgreSQL: columnas Yappy / Yappy manual en payment_config y payment.
-- Equivale a ejecutar migrate_yappy_manual_en1.py + migrate_yappy_manual_checkout_v3.py
-- con la app apuntando a esta BD.
--
-- Uso (ejemplo):
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/sql/postgresql_payment_yappy_manual_en1_v3.sql
--
-- Requiere PostgreSQL 11+ (ADD COLUMN IF NOT EXISTS). Si no, usá los scripts Python en backend/.

-- payment_config (EN1 + checkout v3)
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_directory_name VARCHAR(100);
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_qr_image_path VARCHAR(500);
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_business_name VARCHAR(200);
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_manual_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_manual_instructions TEXT;
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_manual_admin_emails TEXT;

ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_display_name VARCHAR(200);
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_phone_or_identifier VARCHAR(120);
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_merchant_phone VARCHAR(64);
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_instructions TEXT;
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_requires_receipt BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE payment_config ADD COLUMN IF NOT EXISTS yappy_admin_validation_required BOOLEAN NOT NULL DEFAULT TRUE;

-- payment (EN1 + checkout v3)
ALTER TABLE payment ADD COLUMN IF NOT EXISTS amount_received_cents INTEGER;
ALTER TABLE payment ADD COLUMN IF NOT EXISTS validated_by_user_id INTEGER;
ALTER TABLE payment ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP;
ALTER TABLE payment ADD COLUMN IF NOT EXISTS validation_observations TEXT;
ALTER TABLE payment ADD COLUMN IF NOT EXISTS yappy_manual_audit_json TEXT;

ALTER TABLE payment ADD COLUMN IF NOT EXISTS organization_id INTEGER;
ALTER TABLE payment ADD COLUMN IF NOT EXISTS payment_user_reference VARCHAR(500);
ALTER TABLE payment ADD COLUMN IF NOT EXISTS receipt_uploaded_at TIMESTAMP;
ALTER TABLE payment ADD COLUMN IF NOT EXISTS receipt_disk_path VARCHAR(500);
ALTER TABLE payment ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Opcional: ampliar status para estados yappy_manual (falla silenciosa si ya es VARCHAR(32) o mayor)
DO $$
BEGIN
  ALTER TABLE payment ALTER COLUMN status TYPE VARCHAR(32);
EXCEPTION
  WHEN others THEN
    RAISE NOTICE 'payment.status alter omitido: %', SQLERRM;
END $$;
