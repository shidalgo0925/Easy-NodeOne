#!/usr/bin/env bash
# Validación GO IIUS (ejecutar en silo con venv activo).
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source ../.venv/bin/activate 2>/dev/null || source ../../.venv/bin/activate
export NODEONE_BRAND_PRESET="${NODEONE_BRAND_PRESET:-iius}"

echo "=== GO IIUS validate ==="
python3 run_etapa1_dev_validation.py
python3 verify_payments_tenant_setup.py
python3 scripts/test_academic_enrollment_iius.py
python3 scripts/test_academic_gate_iius.py
python3 scripts/test_iius_inscripcion_landings.py
python3 scripts/check_paypal_readiness_iius.py || true
echo "=== LISTO (PayPal exit != 0 es esperado sin client_id) ==="
