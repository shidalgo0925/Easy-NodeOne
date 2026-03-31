"""Registro de rutas admin benefits / plans / policies sobre la app (endpoints legacy)."""


def register_admin_benefits_plans_policies_routes(app):
    from flask import jsonify, render_template, request

    from app import (
        admin_data_scope_organization_id,
        admin_required,
        Benefit,
        db,
        MembershipPlan,
        Policy,
    )

    # ==================== RUTAS ADMIN PARA BENEFICIOS ====================

    @app.route('/admin/benefits')
    @admin_required
    def admin_benefits():
        """Panel de administración de beneficios por membresía"""
        status = request.args.get('status', 'all')
        plan = request.args.get('plan', '')
        q = Benefit.query.filter_by(organization_id=admin_data_scope_organization_id())
        if status == 'active':
            q = q.filter_by(is_active=True)
        elif status == 'inactive':
            q = q.filter_by(is_active=False)
        if plan:
            q = q.filter_by(membership_type=plan)
        benefits = q.order_by(Benefit.membership_type, Benefit.name).all()
        return render_template('admin/benefits.html', benefits=benefits, current_status=status, current_plan=plan)

    @app.route('/api/admin/benefits', methods=['GET'])
    @admin_required
    def admin_benefits_list():
        """Listar beneficios (API)"""
        benefits = Benefit.query.filter_by(organization_id=admin_data_scope_organization_id()).order_by(
            Benefit.membership_type, Benefit.name
        ).all()
        return jsonify({'success': True, 'benefits': [{'id': b.id, 'name': b.name, 'description': b.description, 'membership_type': b.membership_type, 'is_active': b.is_active, 'icon': b.icon, 'color': b.color} for b in benefits]})

    @app.route('/api/admin/benefits/create', methods=['POST'])
    @admin_required
    def admin_benefits_create():
        """Crear beneficio"""
        try:
            data = request.get_json()
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'success': False, 'error': 'Nombre obligatorio'}), 400
            membership_type = (data.get('membership_type') or 'basic').strip().lower()
            b = Benefit(
                name=name,
                description=(data.get('description') or '').strip() or None,
                membership_type=membership_type,
                is_active=data.get('is_active', True),
                icon=(data.get('icon') or '').strip() or None,
                color=(data.get('color') or '').strip() or None,
                organization_id=admin_data_scope_organization_id(),
            )
            db.session.add(b)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Beneficio creado', 'benefit': {'id': b.id, 'name': b.name, 'description': b.description, 'membership_type': b.membership_type, 'is_active': b.is_active, 'icon': b.icon, 'color': b.color}})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    @app.route('/api/admin/benefits/update/<int:benefit_id>', methods=['PUT'])
    @admin_required
    def admin_benefits_update(benefit_id):
        """Actualizar beneficio"""
        try:
            oid = admin_data_scope_organization_id()
            b = Benefit.query.filter_by(id=benefit_id, organization_id=oid).first_or_404()
            data = request.get_json()
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'success': False, 'error': 'Nombre obligatorio'}), 400
            b.name = name
            b.description = (data.get('description') or '').strip() or None
            b.membership_type = (data.get('membership_type') or b.membership_type).strip().lower()
            b.is_active = data.get('is_active', b.is_active)
            b.icon = (data.get('icon') or '').strip() or None
            b.color = (data.get('color') or '').strip() or None
            db.session.commit()
            return jsonify({'success': True, 'message': 'Beneficio actualizado', 'benefit': {'id': b.id, 'name': b.name, 'description': b.description, 'membership_type': b.membership_type, 'is_active': b.is_active, 'icon': b.icon, 'color': b.color}})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    @app.route('/api/admin/benefits/<int:benefit_id>', methods=['GET'])
    @admin_required
    def admin_benefits_get(benefit_id):
        """Obtener un beneficio"""
        oid = admin_data_scope_organization_id()
        b = Benefit.query.filter_by(id=benefit_id, organization_id=oid).first_or_404()
        return jsonify({'success': True, 'benefit': {'id': b.id, 'name': b.name, 'description': b.description, 'membership_type': b.membership_type, 'is_active': b.is_active, 'icon': b.icon, 'color': b.color}})

    @app.route('/api/admin/benefits/delete/<int:benefit_id>', methods=['DELETE'])
    @admin_required
    def admin_benefits_delete(benefit_id):
        """Eliminar beneficio"""
        try:
            oid = admin_data_scope_organization_id()
            b = Benefit.query.filter_by(id=benefit_id, organization_id=oid).first_or_404()
            db.session.delete(b)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Beneficio eliminado'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    # ==================== RUTAS ADMIN PARA PLANES DE MEMBRESÍA ====================

    @app.route('/admin/plans')
    @admin_required
    def admin_plans():
        """Panel de administración de planes de membresía"""
        oid = admin_data_scope_organization_id()
        plans = MembershipPlan.query.filter_by(organization_id=oid).order_by(
            MembershipPlan.display_order, MembershipPlan.level
        ).all()
        return render_template('admin/plans.html', plans=plans)

    @app.route('/api/admin/plans/create', methods=['POST'])
    @admin_required
    def admin_plans_create():
        """Crear plan"""
        try:
            data = request.get_json()
            slug = (data.get('slug') or '').strip().lower().replace(' ', '_')
            if not slug:
                return jsonify({'success': False, 'error': 'Slug obligatorio'}), 400
            oid = admin_data_scope_organization_id()
            if MembershipPlan.query.filter_by(slug=slug, organization_id=oid).first():
                return jsonify({'success': False, 'error': 'Ya existe un plan con ese slug'}), 400
            p = MembershipPlan(
                slug=slug,
                name=(data.get('name') or slug).strip(),
                description=(data.get('description') or '').strip() or None,
                price_yearly=float(data.get('price_yearly', 0)),
                price_monthly=float(data.get('price_monthly', 0)),
                display_order=int(data.get('display_order', 0)),
                level=int(data.get('level', 0)),
                badge=(data.get('badge') or '').strip() or None,
                color=(data.get('color') or 'bg-secondary').strip(),
                is_active=data.get('is_active', True),
                organization_id=oid,
            )
            db.session.add(p)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Plan creado', 'plan': p.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    @app.route('/api/admin/plans/update/<int:plan_id>', methods=['PUT'])
    @admin_required
    def admin_plans_update(plan_id):
        """Actualizar plan"""
        try:
            oid = admin_data_scope_organization_id()
            p = MembershipPlan.query.filter_by(id=plan_id, organization_id=oid).first_or_404()
            data = request.get_json()
            p.name = (data.get('name') or p.name).strip()
            p.description = (data.get('description') or '').strip() or None
            p.price_yearly = float(data.get('price_yearly', p.price_yearly))
            p.price_monthly = float(data.get('price_monthly', p.price_monthly))
            p.display_order = int(data.get('display_order', p.display_order))
            p.level = int(data.get('level', p.level))
            p.badge = (data.get('badge') or '').strip() or None
            p.color = (data.get('color') or p.color).strip()
            p.is_active = data.get('is_active', p.is_active)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Plan actualizado', 'plan': p.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    @app.route('/api/admin/plans/<int:plan_id>', methods=['GET'])
    @admin_required
    def admin_plans_get(plan_id):
        """Obtener un plan"""
        oid = admin_data_scope_organization_id()
        p = MembershipPlan.query.filter_by(id=plan_id, organization_id=oid).first_or_404()
        return jsonify({'success': True, 'plan': p.to_dict()})

    @app.route('/api/admin/plans/delete/<int:plan_id>', methods=['DELETE'])
    @admin_required
    def admin_plans_delete(plan_id):
        """Eliminar plan (cuidado: suscripciones/beneficios pueden seguir referenciando el slug)"""
        try:
            oid = admin_data_scope_organization_id()
            p = MembershipPlan.query.filter_by(id=plan_id, organization_id=oid).first_or_404()
            db.session.delete(p)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Plan eliminado'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    # ==================== RUTAS ADMIN PARA NORMATIVAS (POLÍTICAS) ====================

    @app.route('/admin/policies')
    @admin_required
    def admin_policies():
        """Panel de administración de políticas institucionales"""
        status = request.args.get('status', 'all')
        q = Policy.query.order_by(Policy.title)
        if status == 'active':
            q = q.filter_by(is_active=True)
        elif status == 'inactive':
            q = q.filter_by(is_active=False)
        policies = q.all()
        return render_template('admin/policies.html', policies=policies, current_status=status)

    @app.route('/api/admin/policies/create', methods=['POST'])
    @admin_required
    def admin_policies_create():
        """Crear política"""
        try:
            data = request.get_json()
            slug = (data.get('slug') or '').strip().lower().replace(' ', '-')
            if not slug:
                return jsonify({'success': False, 'error': 'Slug obligatorio'}), 400
            if Policy.query.filter_by(slug=slug).first():
                return jsonify({'success': False, 'error': 'Ya existe una política con ese slug'}), 400
            p = Policy(
                title=(data.get('title') or slug).strip(),
                slug=slug,
                content=(data.get('content') or '').strip() or None,
                version=(data.get('version') or '1.0').strip(),
                is_active=data.get('is_active', True),
            )
            db.session.add(p)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Política creada', 'policy': p.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    @app.route('/api/admin/policies/update/<int:policy_id>', methods=['PUT'])
    @admin_required
    def admin_policies_update(policy_id):
        """Actualizar política (permite cambiar versión y contenido)"""
        try:
            p = Policy.query.get_or_404(policy_id)
            data = request.get_json()
            p.title = (data.get('title') or p.title).strip()
            p.content = (data.get('content') or p.content or '').strip() or None
            p.version = (data.get('version') or p.version or '1.0').strip()
            p.is_active = data.get('is_active', p.is_active)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Política actualizada', 'policy': p.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    @app.route('/api/admin/policies/<int:policy_id>', methods=['GET'])
    @admin_required
    def admin_policies_get(policy_id):
        """Obtener una política"""
        p = Policy.query.get_or_404(policy_id)
        return jsonify({'success': True, 'policy': p.to_dict()})

    @app.route('/api/admin/policies/<int:policy_id>/acceptances', methods=['GET'])
    @admin_required
    def admin_policies_acceptances(policy_id):
        """Listar aceptaciones de una política"""
        Policy.query.get_or_404(policy_id)
        from _app.modules.policies.repository import get_acceptances_for_policy

        acceptances = get_acceptances_for_policy(policy_id)
        out = []
        for a in acceptances:
            u = a.user
            out.append({
                'id': a.id,
                'user_id': u.id if u else None,
                'user_email': u.email if u else None,
                'user_name': f'{getattr(u, "first_name", "") or ""} {getattr(u, "last_name", "") or ""}'.strip() if u else '',
                'accepted_at': a.accepted_at.isoformat() if a.accepted_at else None,
                'version': a.version,
                'ip_address': a.ip_address,
            })
        return jsonify({'success': True, 'acceptances': out})

    @app.route('/api/admin/policies/delete/<int:policy_id>', methods=['DELETE'])
    @admin_required
    def admin_policies_delete(policy_id):
        """Eliminar política (y sus aceptaciones por CASCADE)"""
        try:
            p = Policy.query.get_or_404(policy_id)
            db.session.delete(p)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Política eliminada'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
