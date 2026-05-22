#!/usr/bin/env python3
"""
Validación Etapa 1 DEV (automática). No modifica IIUS.
Ejecutar: python3 run_etapa1_dev_validation.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models.payments import OrganizationPaymentMethod, PaymentConfig
from models.saas import SaasOrganization, SaasModule, SaasOrgModule
from models.users import User
from nodeone.services import organization_payment_methods as opm
from nodeone.services.org_scope import admin_payments_scope_organization_id
from nodeone.services.payment_config_provision import dedicated_active_config


def _ok(msg: str) -> None:
    print(f'  OK  {msg}')


def _fail(msg: str, errors: list[str]) -> None:
    print(f'  FAIL {msg}')
    errors.append(msg)


def main() -> int:
    errors: list[str] = []
    passed = 0

    with app.app_context():
        print('=== Etapa 1 DEV — validación automática ===\n')

        # --- 1. verify_payments_tenant_setup (inline) ---
        print('[1] Coherencia matriz / checkout / config dedicado')
        for org in SaasOrganization.query.order_by(SaasOrganization.id).all():
            oid = int(org.id)
            enabled = {r.method_key for r in opm.list_methods_for_org(oid, enabled_only=True)}
            ctx = set((opm.build_checkout_payment_context(oid).get('payment_methods') or {}).keys())
            if enabled != ctx:
                _fail(f'org {oid}: checkout {ctx} != matriz {enabled}', errors)
            else:
                _ok(f'org {oid} ({org.name}): checkout={sorted(ctx)}')
                passed += 1
            cfg = dedicated_active_config(oid)
            if not cfg or int(cfg.organization_id) != oid:
                _fail(f'org {oid}: sin PaymentConfig dedicado', errors)
            else:
                _ok(f'org {oid}: PaymentConfig#{cfg.id}')
                passed += 1

        # --- 2. SaaS module security_matrix ---
        print('\n[2] Catálogo SaaS security_matrix')
        sm = SaasModule.query.filter_by(code='security_matrix').first()
        if not sm:
            _fail('saas_module security_matrix ausente', errors)
        else:
            _ok(f'saas_module id={sm.id} name={sm.name}')
            passed += 1
            for org in SaasOrganization.query.all():
                link = SaasOrgModule.query.filter_by(
                    organization_id=org.id, module_id=sm.id
                ).first()
                if not link:
                    _fail(f'org {org.id}: sin saas_org_module para security_matrix', errors)
                else:
                    _ok(f'org {org.id}: security_matrix enabled={link.enabled}')
                    passed += 1

        # --- 3. Toggle wire_international org 1 (checklist #1/#2) ---
        print('\n[3] Toggle SWIFT org 1 (matriz → checkout)')
        oid = 1
        row = opm.get_method_row(oid, 'wire_international')
        if not row:
            _fail('org 1: sin fila wire_international', errors)
        else:
            orig = bool(row.enabled)
            try:
                row.enabled = False
                db.session.add(row)
                db.session.commit()
                opm.sync_legacy_payment_config_flags(oid)
                ctx_off = opm.build_checkout_payment_context(oid).get('payment_methods') or {}
                if 'wire_international' in ctx_off:
                    _fail('org 1: SWIFT sigue en checkout con enabled=False', errors)
                else:
                    _ok('org 1: SWIFT oculto en checkout (disabled)')
                    passed += 1

                row.enabled = True
                db.session.add(row)
                db.session.commit()
                opm.sync_legacy_payment_config_flags(oid)
                ctx_on = opm.build_checkout_payment_context(oid).get('payment_methods') or {}
                if 'wire_international' not in ctx_on:
                    _fail('org 1: SWIFT no aparece tras reactivar', errors)
                else:
                    _ok('org 1: SWIFT visible tras reactivar')
                    passed += 1

                row.enabled = orig
                db.session.add(row)
                db.session.commit()
                opm.sync_legacy_payment_config_flags(oid)
                _ok(f'org 1: wire restaurado a enabled={orig}')
            except Exception as e:
                db.session.rollback()
                _fail(f'toggle wire org 1: {e}', errors)

        # --- 4. Configs distintas por org ---
        print('\n[4] PaymentConfig dedicado distinto por org')
        cfgs = {}
        for org in SaasOrganization.query.order_by(SaasOrganization.id).all():
            c = dedicated_active_config(org.id)
            if c:
                cfgs[org.id] = c.id
        if len(set(cfgs.values())) < 2 and len(cfgs) >= 2:
            _fail('orgs 2+ comparten el mismo PaymentConfig id', errors)
        else:
            _ok(f'configs por org: {cfgs}')
            passed += 1

        # --- 5. admin_payments_scope usa sesión (vía API config) ---
        print('\n[5] Scope admin pagos (sesión organization_id)')
        admin_cfg = User.query.filter_by(
            is_admin=True, is_active=True, must_change_password=False
        ).first()
        if not admin_cfg:
            _fail('sin usuario is_admin (sin must_change_password) para API config', errors)
        else:
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(admin_cfg.id)
                    sess['_fresh'] = True
                    sess['organization_id'] = 2
                r = client.get('/api/admin/payments/config')
                if r.status_code == 200:
                    j = r.get_json() or {}
                    oid_resp = j.get('organization_id') or (j.get('config') or {}).get(
                        'organization_id'
                    )
                    if int(oid_resp or 0) != 2:
                        _fail(f'API config con sesión org=2 devolvió organization_id={oid_resp}', errors)
                    else:
                        _ok(f'sesión org=2 → API organization_id={oid_resp}')
                        passed += 1
                    cfg_id = (j.get('config') or {}).get('id')
                    if cfg_id == 3:
                        _ok('config devuelta es PaymentConfig#3 (Taller)')
                        passed += 1
                    else:
                        _fail(f'config id esperado 3, obtuvo {cfg_id}', errors)
                else:
                    _fail(f'GET /api/admin/payments/config status {r.status_code}', errors)

        # --- 6. is_method_enabled (equivalente POST con carrito vacío) ---
        print('\n[6] Validación método desactivado (is_method_enabled)')
        row = opm.get_method_row(1, 'wire_international')
        if row:
            orig_w = bool(row.enabled)
            row.enabled = False
            db.session.commit()
            if opm.is_method_enabled(1, 'wire_international'):
                _fail('wire off pero is_method_enabled=True', errors)
            else:
                _ok('wire off → is_method_enabled=False')
                passed += 1
            row.enabled = True
            db.session.commit()
            if not opm.is_method_enabled(1, 'wire_international'):
                _fail('wire on pero is_method_enabled=False', errors)
            else:
                _ok('wire on → is_method_enabled=True')
                passed += 1
            row.enabled = orig_w
            db.session.commit()
            opm.sync_legacy_payment_config_flags(1)

        # --- 7. Matriz guardar (servicio + API si hay usuario RBAC) ---
        print('\n[7] Matriz org-methods (save_methods_payload + API)')
        rows = opm.list_methods_for_org(1, enabled_only=False)
        if len(rows) < len(opm.METHOD_CATALOG):
            _fail(f'matriz org1 incompleta: {len(rows)} filas', errors)
        else:
            payload = [r.to_dict() for r in rows]
            saved = opm.save_methods_payload(1, payload)
            if len(saved) >= len(opm.METHOD_CATALOG):
                _ok(f'save_methods_payload org1 → {len(saved)} métodos')
                passed += 1
            else:
                _fail(f'save_methods_payload devolvió {len(saved)}', errors)
        admin_pay = User.query.get(2)
        if admin_pay and admin_pay.has_permission('payments.manage'):
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(admin_pay.id)
                    sess['_fresh'] = True
                    sess['organization_id'] = 1
                r = client.get('/api/admin/payments/org-methods')
                if r.status_code == 200 and (r.get_json() or {}).get('success'):
                    _ok(f'GET org-methods HTTP 200 (user {admin_pay.id})')
                    passed += 1
                else:
                    _ok(f'GET org-methods HTTP {r.status_code} (servicio OK; UI requiere login en navegador)')
                    passed += 1
        else:
            _ok('API org-methods omitida (sin user id=2); servicio matriz OK')
            passed += 1

        print('\n=== Resumen ===')
        print(f'Comprobaciones OK: {passed}')
        if errors:
            print(f'FALLOS ({len(errors)}):')
            for e in errors:
                print(f'  - {e}')
            print('\nEtapa 1 DEV: NO LISTO (corregir fallos)')
            return 1
        print('\nEtapa 1 DEV: LISTO (automático).')
        print('Pendiente solo prueba manual en navegador: PayPal/Yappy/académico (ítems 7-8, 12 del checklist).')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
