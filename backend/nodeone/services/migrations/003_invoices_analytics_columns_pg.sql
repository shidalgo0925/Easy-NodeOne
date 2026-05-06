-- Alinea tabla ``invoices`` con ``nodeone.modules.accounting.models.Invoice``
-- (evita 500 en /admin/analytics al consultar ``amount_paid`` y residuales).
-- PostgreSQL. Ejecutar como superusuario o owner de la BD.

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS journal_entry_id INTEGER;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_journal_entry_id INTEGER;

CREATE INDEX IF NOT EXISTS ix_invoices_journal_entry_id ON invoices (journal_entry_id);
CREATE INDEX IF NOT EXISTS ix_invoices_payment_journal_entry_id ON invoices (payment_journal_entry_id);
