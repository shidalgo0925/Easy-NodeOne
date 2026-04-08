"""Compat legacy: /admin/contacts redirige a CRM y migra contactos a leads."""


def register_admin_tenant_contacts_routes(app):
    from flask import flash, redirect, url_for
    from flask_login import current_user

    from app import admin_required, db, TenantCrmContact
    from nodeone.modules.crm_api.models import CrmLead, CrmStage

    def _migrate_contacts_to_leads():
        rows = TenantCrmContact.query.order_by(TenantCrmContact.id.asc()).all()
        if not rows:
            return 0
        moved = 0
        for c in rows:
            stage = (
                CrmStage.query
                .filter_by(organization_id=int(c.organization_id), is_won=False, is_lost=False)
                .order_by(CrmStage.sequence.asc())
                .first()
            )
            if stage is None:
                continue
            exists = CrmLead.query.filter_by(
                organization_id=int(c.organization_id),
                name=(c.name or '').strip(),
                email=(c.email or '').strip() or None,
                phone=(c.phone or '').strip() or None,
            ).first()
            if exists:
                continue
            row = CrmLead(
                organization_id=int(c.organization_id),
                lead_type='lead',
                name=(c.name or 'Contacto').strip(),
                contact_name=(c.name or '').strip() or None,
                company_name=(c.company or '').strip() or None,
                email=(c.email or '').strip() or None,
                phone=(c.phone or '').strip() or None,
                stage_id=stage.id,
                user_id=int(getattr(current_user, 'id', 0) or 0) or None,
                expected_revenue=0.0,
                probability=float(stage.probability_default or 0),
                priority='low',
                source='crm_contacts_migration',
                description=(c.notes or '').strip() or None,
                active=True,
            )
            db.session.add(row)
            moved += 1
        if moved:
            db.session.commit()
        return moved

    @app.route('/admin/contacts', methods=['GET', 'POST'])
    @admin_required
    def admin_tenant_contacts():
        moved = _migrate_contacts_to_leads()
        if moved:
            flash(f'Se migraron {moved} contactos a CRM.', 'info')
        flash('Contactos fue unificado en CRM. Usa el módulo CRM.', 'info')
        return redirect(url_for('admin_crm_dashboard'))

    @app.route('/admin/contacts/<int:cid>/delete', methods=['POST'])
    @admin_required
    def admin_tenant_contact_delete(cid):
        flash('Contactos fue unificado en CRM. Usa el módulo CRM.', 'info')
        return redirect(url_for('admin_crm_dashboard'))
