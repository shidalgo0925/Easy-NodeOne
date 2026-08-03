-- Snapshot congelado al emitir certificados de membresía (regeneración masiva admin).
-- PostgreSQL. Ejecutar como superusuario o owner de la BD.

ALTER TABLE certificates ADD COLUMN IF NOT EXISTS emission_snapshot TEXT;
