"""Registro de rutas admin users/roles/permissions en app (endpoints legacy)."""

from sqlalchemy import insert, text as sql_text


def _user_has_role_sa(user) -> bool:
    """Rol SA (SuperAdministrador) en RBAC; puede gestionar el flag is_admin aunque la columna esté desincronizada."""
    if user is None or not getattr(user, 'id', None):
        return False
    from app import db

    r = db.session.execute(
        sql_text(
            'SELECT 1 FROM user_role ur JOIN role r ON r.id = ur.role_id '
            "WHERE ur.user_id = :uid AND r.code = 'SA' LIMIT 1"
        ),
        {'uid': int(user.id)},
    ).fetchone()
    return r is not None


def can_manage_platform_superuser_fields(user) -> bool:
    """Quién puede ver/editar is_admin en UI y backend: flag plataforma o rol SA."""
    return bool(getattr(user, 'is_admin', False)) or _user_has_role_sa(user)


def apply_operator_filter(query, model, field_name, value):
    """Aplica filtro con soporte para negación usando '!' al inicio."""
    if not value:
        return query
    column = getattr(model, field_name)
    if isinstance(value, str) and value.startswith('!'):
        return query.filter(column != value[1:])
    return query.filter(column == value)


def register_admin_users_roles_routes(app):
    from app import (
        ActivityLog,
        admin_data_scope_organization_id,
        admin_required,
        Advisor,
        db,
        Permission,
        require_permission,
        Role,
        role_permission_table,
        SaasOrganization,
        Subscription,
        user_role_table,
        User,
        validate_cedula_or_passport,
        validate_country,
        validate_email_format,
        VALID_COUNTRIES,
    )
    from flask import flash, jsonify, redirect, render_template, request, url_for
    from flask_login import current_user

    from nodeone.services.user_organization import ensure_membership, user_has_active_membership, user_in_org_clause

    def _user_in_scope_or_404(uid):
        scope = admin_data_scope_organization_id()
        return User.query.filter(User.id == uid).filter(user_in_org_clause(User, scope)).first_or_404()

    @app.route('/admin/users')
    @require_permission('users.view')
    def admin_users():
        """Gestión de usuarios con filtros (autorización por permiso users.view). Soporta ! para negación."""
        # Obtener parámetros de filtro
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', 'all')
        admin_filter = request.args.get('admin', 'all')
        advisor_filter = request.args.get('advisor', 'all')
        group_filter = request.args.get('group', 'all')
        tag_filter = request.args.get('tag', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # is_admin (columna) o rol SA: pueden ver casilla "Es Administrador" y filtro por organización
        is_platform_admin = can_manage_platform_superuser_fields(current_user)
        users_organization_filter = None
        # Construir query base: empresa activa (sesión / selector); admin plataforma puede acotar por ?organization_id=
        scope_oid = admin_data_scope_organization_id()
        if is_platform_admin:
            org_param = request.args.get('organization_id', type=int)
            if org_param:
                scope_oid = org_param
                users_organization_filter = org_param

        saas_organizations = []
        if is_platform_admin:
            from utils.organization import platform_visible_organization_ids

            _rows = (
                SaasOrganization.query.filter_by(is_active=True)
                .order_by(SaasOrganization.name.asc(), SaasOrganization.id.asc())
                .all()
            )
            _allow = platform_visible_organization_ids()
            if _allow is not None:
                _rows = [o for o in _rows if int(o.id) in _allow]
            saas_organizations = _rows

        query = User.query.filter(user_in_org_clause(User, scope_oid))

        # Filtro de búsqueda (nombre, email, teléfono)
        if search:
            query = query.filter(
                db.or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.phone.ilike(f'%{search}%')
                )
            )
    
        # Filtro de estado (soporta !active / !inactive)
        if status_filter and status_filter != 'all':
            negate = status_filter.startswith("!")
            raw = status_filter[1:].strip() if negate else status_filter
            is_active_val = (raw == 'active')
            if negate:
                query = query.filter(User.is_active != is_active_val)
            else:
                query = query.filter(User.is_active == is_active_val)
    
        # Filtro de admin (boolean: 1/yes/true -> True; soporta !)
        if admin_filter and admin_filter not in ('all', ''):
            negate = admin_filter.startswith("!")
            raw = (admin_filter[1:].strip() if negate else admin_filter).lower()
            bool_val = raw in ('1', 'true', 'yes')
            if negate:
                query = query.filter(User.is_admin != bool_val)
            else:
                query = query.filter(User.is_admin == bool_val)
    
        # Filtro de asesor (boolean; soporta !)
        if advisor_filter and advisor_filter not in ('all', ''):
            negate = advisor_filter.startswith("!")
            raw = (advisor_filter[1:].strip() if negate else advisor_filter).lower()
            bool_val = raw in ('1', 'true', 'yes')
            if negate:
                query = query.filter(User.is_advisor != bool_val)
            else:
                query = query.filter(User.is_advisor == bool_val)
    
        # Filtro de grupo (soporta exclusión con prefijo ! en slug)
        if group_filter and group_filter != 'all':
            query = apply_operator_filter(query, User, 'user_group', group_filter)
    
        # Filtro de etiqueta
        if tag_filter:
            query = query.filter(User.tags.ilike(f'%{tag_filter}%'))
    
        # Ordenar y paginar
        query = query.order_by(User.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items
    
        # Obtener grupos únicos para el filtro (misma empresa)
        groups = db.session.query(User.user_group).distinct().filter(
            User.user_group.isnot(None),
            user_in_org_clause(User, scope_oid),
        ).all()
        groups = [g[0] for g in groups if g[0]]
    
        # Obtener etiquetas únicas para el filtro (extraer de todos los tags)
        all_tags = db.session.query(User.tags).filter(
            User.tags.isnot(None),
            user_in_org_clause(User, scope_oid),
        ).all()
        unique_tags = set()
        for tag_str in all_tags:
            if tag_str[0]:
                unique_tags.update([t.strip() for t in tag_str[0].split(',') if t.strip()])
        unique_tags = sorted(list(unique_tags))
    
        # Obtener membresías activas para cada usuario (para mostrar en la tabla)
        user_memberships = {}
        for user in users:
            active_membership = user.get_active_membership()
            if active_membership:
                # Determinar tipo de membresía y fecha de expiración
                if isinstance(active_membership, Subscription):
                    user_memberships[user.id] = {
                        'type': active_membership.membership_type,
                        'end_date': active_membership.end_date,
                        'status': active_membership.status,
                        'is_subscription': True
                    }
                else:
                    user_memberships[user.id] = {
                        'type': active_membership.membership_type,
                        'end_date': active_membership.end_date,
                        'status': 'active' if active_membership.is_active else 'expired',
                        'is_subscription': False
                    }
    
        return render_template(
            'admin/users.html',
            users=users,
            pagination=pagination,
            search=search,
            status_filter=status_filter,
            admin_filter=admin_filter,
            advisor_filter=advisor_filter,
            group_filter=group_filter,
            tag_filter=tag_filter,
            groups=groups,
            unique_tags=unique_tags,
            valid_countries=VALID_COUNTRIES,
            user_memberships=user_memberships,
            can_filter_users_by_org=is_platform_admin,
            saas_organizations=saas_organizations,
            users_organization_filter=users_organization_filter,
        )


    @app.route('/admin/users/<int:user_id>/update', methods=['POST'])
    @require_permission('users.update')
    def admin_update_user(user_id):
        """Actualizar atributos básicos del usuario (admin, asesor, estado)."""
        user = _user_in_scope_or_404(user_id)
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        country = request.form.get('country', '').strip()
        cedula_or_passport = request.form.get('cedula_or_passport', '').strip()

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.phone = phone or None
    
        # Actualizar país con validación
        if country:
            is_valid, error_message = validate_country(country)
            if not is_valid:
                flash(error_message, 'error')
                return redirect(url_for('admin_users'))
            user.country = country
        else:
            user.country = None
    
        # Actualizar cédula o pasaporte con validación
        if cedula_or_passport:
            is_valid, error_message = validate_cedula_or_passport(cedula_or_passport, country or user.country)
            if not is_valid:
                flash(error_message, 'error')
                return redirect(url_for('admin_users'))
            user.cedula_or_passport = cedula_or_passport
        else:
            user.cedula_or_passport = None
    
        # Actualizar tags y grupo
        user.tags = request.form.get('tags', '').strip() or None
        user.user_group = request.form.get('user_group', '').strip() or None
    
        # Actualizar email si cambió
        new_email = request.form.get('email', '').strip()
        if new_email and new_email != user.email:
            # Validar formato de email
            is_valid, error_message = validate_email_format(new_email)
            if not is_valid:
                flash(error_message, 'error')
                return redirect(url_for('admin_users'))
            # Verificar que el nuevo email no esté en uso
            if User.query.filter_by(email=new_email.lower()).first():
                flash('El email ya está en uso por otro usuario.', 'error')
                return redirect(url_for('admin_users'))
            user.email = new_email.lower()
    
        # Actualizar contraseña si se proporcionó
        new_password = request.form.get('password', '').strip()
        if new_password:
            if len(new_password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'error')
                return redirect(url_for('admin_users'))
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(new_password)

        user.is_active = bool(request.form.get('is_active'))
        if can_manage_platform_superuser_fields(current_user):
            user.is_admin = bool(request.form.get('is_admin'))
        user.is_salesperson = bool(request.form.get('is_salesperson'))
        wants_advisor = bool(request.form.get('is_advisor'))

        if wants_advisor and not user.is_advisor:
            user.is_advisor = True
            if not user.advisor_profile:
                new_profile = Advisor(
                    user_id=user.id,
                    headline=request.form.get('advisor_headline', '').strip() or 'Asesor Easy NodeOne',
                    specializations=request.form.get('advisor_specializations', '').strip(),
                    meeting_url=request.form.get('advisor_meeting_url', '').strip(),
                )
                db.session.add(new_profile)
        elif not wants_advisor and user.is_advisor:
            user.is_advisor = False
            if user.advisor_profile:
                db.session.delete(user.advisor_profile)

        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/create', methods=['POST'])
    @admin_required
    def admin_create_user():
        """Crear un nuevo usuario"""
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            phone = request.form.get('phone', '').strip()
            country = request.form.get('country', '').strip()
            cedula_or_passport = request.form.get('cedula_or_passport', '').strip()
            is_active = bool(request.form.get('is_active'))
            is_admin = (
                bool(request.form.get('is_admin'))
                if can_manage_platform_superuser_fields(current_user)
                else False
            )
            is_advisor = bool(request.form.get('is_advisor'))
            is_salesperson = bool(request.form.get('is_salesperson'))
            tags = request.form.get('tags', '').strip() or None
            user_group = request.form.get('user_group', '').strip() or None
        
            # Validaciones
            if not first_name or not last_name or not email or not password:
                flash('Todos los campos obligatorios deben ser completados.', 'error')
                return redirect(url_for('admin_users'))
        
            if len(password) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'error')
                return redirect(url_for('admin_users'))
        
            # Validar formato de email
            is_valid, error_message = validate_email_format(email)
            if not is_valid:
                flash(error_message, 'error')
                return redirect(url_for('admin_users'))
        
            # Validar país si se proporciona
            if country:
                is_valid, error_message = validate_country(country)
                if not is_valid:
                    flash(error_message, 'error')
                    return redirect(url_for('admin_users'))
        
            # Validar cédula o pasaporte si se proporciona
            if cedula_or_passport:
                is_valid, error_message = validate_cedula_or_passport(cedula_or_passport, country)
                if not is_valid:
                    flash(error_message, 'error')
                    return redirect(url_for('admin_users'))
        
            # Verificar si el email ya existe
            if User.query.filter_by(email=email.lower()).first():
                flash('El email ya está registrado.', 'error')
                return redirect(url_for('admin_users'))

            # Organización: scope del admin; si el modal envía organization_id (admin plataforma), usarla.
            org_for_user = int(admin_data_scope_organization_id())
            if can_manage_platform_superuser_fields(current_user):
                from utils.organization import platform_visible_organization_ids

                form_oid = request.form.get('organization_id', type=int)
                if form_oid and form_oid > 0:
                    allow = platform_visible_organization_ids()
                    if allow is not None and form_oid not in allow:
                        flash('Organización no permitida para tu cuenta de administración.', 'error')
                        return redirect(url_for('admin_users'))
                    if not SaasOrganization.query.filter_by(id=form_oid, is_active=True).first():
                        flash('La organización seleccionada no existe o está inactiva.', 'error')
                        return redirect(url_for('admin_users'))
                    org_for_user = form_oid

            # Crear usuario + membresía + perfil asesor en un solo commit (evita is_advisor sin fila Advisor).
            from werkzeug.security import generate_password_hash

            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email.lower(),
                password_hash=generate_password_hash(password),
                phone=phone or None,
                country=country if country else None,
                cedula_or_passport=cedula_or_passport if cedula_or_passport else None,
                tags=tags,
                user_group=user_group,
                is_active=is_active,
                is_admin=is_admin,
                is_advisor=is_advisor,
                is_salesperson=is_salesperson,
                organization_id=org_for_user,
            )
            db.session.add(new_user)
            db.session.flush()
            ensure_membership(new_user.id, int(org_for_user))
            if is_advisor:
                db.session.add(
                    Advisor(
                        user_id=new_user.id,
                        headline='Asesor Easy NodeOne',
                        specializations='',
                        meeting_url='',
                    )
                )
            db.session.commit()

            flash(f'Usuario {first_name} {last_name} creado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'error')
    
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @require_permission('users.delete')
    def admin_delete_user(user_id):
        """Eliminar un usuario"""
        user = _user_in_scope_or_404(user_id)
    
        # No permitir eliminar al usuario actual
        if user.id == current_user.id:
            flash('No puedes eliminar tu propio usuario.', 'error')
            return redirect(url_for('admin_users'))
    
        try:
            user_name = f"{user.first_name} {user.last_name}"
        
            # Eliminar perfil de asesor si existe
            if user.advisor_profile:
                db.session.delete(user.advisor_profile)
        
            # Eliminar usuario
            db.session.delete(user)
            db.session.commit()
        
            flash(f'Usuario {user_name} eliminado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar usuario: {str(e)}', 'error')
    
        return redirect(url_for('admin_users'))


    # ---------------------------------------------------------------------------
    # FASE 5: Asignación de roles a usuarios (API + auditoría)
    # ---------------------------------------------------------------------------

    @app.route('/api/admin/users')
    @require_permission('users.view')
    def api_admin_users():
        """API: listado de usuarios (id, email, nombre, estado, roles). Paginado."""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 25, type=int), 100)
        search = request.args.get('search', '').strip()
        scope = admin_data_scope_organization_id()
        query = User.query.filter(user_in_org_clause(User, scope))
        if search:
            query = query.filter(
                db.or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                )
            )
        query = query.order_by(User.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        users_out = []
        for u in pagination.items:
            roles_codes = [r.code for r in u.roles.all()]
            users_out.append({
                'id': u.id,
                'email': u.email,
                'first_name': u.first_name or '',
                'last_name': u.last_name or '',
                'is_active': u.is_active,
                'roles': roles_codes,
            })
        return jsonify({
            'users': users_out,
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages,
        })


    def _get_user_role_ids(user_id):
        """Obtener IDs de roles del usuario vía SQL directo (evita fallos de relación User.roles en prod)."""
        try:
            rows = db.session.execute(
                sql_text('SELECT role_id FROM user_role WHERE user_id = :uid'),
                {'uid': user_id}
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            db.session.rollback()
            return []


    @app.route('/api/admin/users/<int:user_id>/roles')
    @require_permission('roles.assign')
    def api_admin_user_roles(user_id):
        """API: roles del usuario + roles disponibles para asignar (excl. SA)."""
        try:
            user = _user_in_scope_or_404(user_id)
            # Roles del usuario vía SQL directo; si falla (ej. tabla distinta en prod), usar vacío
            try:
                role_rows = db.session.execute(
                    sql_text('SELECT r.id, r.code, r.name FROM role r INNER JOIN user_role ur ON ur.role_id = r.id WHERE ur.user_id = :uid'),
                    {'uid': user_id}
                ).fetchall()
            except Exception as e:
                db.session.rollback()
                app.logger.warning('api_admin_user_roles query user_role failed: %s', e)
                role_rows = []
            current_roles = [
                {'id': r[0], 'code': (r[1] or ''), 'name': (r[2] or ''), 'system': (r[1] == 'SA')}
                for r in role_rows
            ]
            user_role_ids = {r[0] for r in role_rows}
            all_roles = Role.query.filter(Role.code != 'SA').order_by(Role.code).all()
            available_roles = [
                {'id': r.id, 'code': getattr(r, 'code', ''), 'name': getattr(r, 'name', '')}
                for r in all_roles if r.id not in user_role_ids
            ]
            return jsonify({
                'user': {
                    'id': user.id,
                    'email': str(user.email) if user.email else '',
                    'first_name': (user.first_name or '') if user.first_name else '',
                    'last_name': (user.last_name or '') if user.last_name else '',
                    'is_active': bool(user.is_active),
                },
                'current_roles': current_roles,
                'available_roles': available_roles,
            })
        except Exception as e:
            db.session.rollback()
            app.logger.exception('api_admin_user_roles error: %s', e)
            return jsonify({'error': 'Error al cargar roles', 'message': str(e)}), 500


    @app.route('/api/admin/users/<int:user_id>/roles', methods=['POST'])
    @require_permission('roles.assign')
    def api_admin_user_roles_assign(user_id):
        """Asignar un rol al usuario. Body: { \"role_id\": N }."""
        _user_in_scope_or_404(user_id)
        data = request.get_json() or {}
        role_id = data.get('role_id')
        if role_id is None:
            return jsonify({'success': False, 'error': 'role_id requerido'}), 400
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'success': False, 'error': 'Rol no encontrado'}), 404
        if role.code == 'SA':
            return jsonify({'success': False, 'error': 'No se puede asignar el rol SA'}), 403
        if role_id in _get_user_role_ids(user_id):
            return jsonify({'success': False, 'error': 'El usuario ya tiene este rol'}), 400
        try:
            db.session.execute(
                insert(user_role_table).values(
                    user_id=user_id,
                    role_id=role_id,
                    assigned_by_id=current_user.id,
                )
            )
            ActivityLog.log_activity(
                current_user.id, 'ASSIGN_ROLE', 'user_role', user_id,
                f'role={role.code} user={user_id} assigned', request
            )
            db.session.commit()
            return jsonify({'success': True, 'message': f'Rol {role.code} asignado'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/admin/users/<int:user_id>/roles/<int:role_id>', methods=['DELETE'])
    @require_permission('roles.assign')
    def api_admin_user_roles_remove(user_id, role_id):
        """Quitar un rol al usuario."""
        _user_in_scope_or_404(user_id)
        role = Role.query.get_or_404(role_id)
        if role.code == 'SA':
            return jsonify({'success': False, 'error': 'No se puede modificar el rol SA'}), 403
        if role_id not in _get_user_role_ids(user_id):
            return jsonify({'success': False, 'error': 'El usuario no tiene este rol'}), 400
        try:
            db.session.execute(
                user_role_table.delete().where(
                    user_role_table.c.user_id == user_id,
                    user_role_table.c.role_id == role_id,
                )
            )
            ActivityLog.log_activity(
                current_user.id, 'UNASSIGN_ROLE', 'user_role', user_id,
                f'role={role.code} user={user_id} removed', request
            )
            db.session.commit()
            return jsonify({'success': True, 'message': f'Rol {role.code} quitado'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/admin/users/<int:user_id>/roles')
    @require_permission('roles.assign')
    def admin_user_roles_page(user_id):
        """Pantalla de asignación de roles al usuario (UI)."""
        try:
            user = _user_in_scope_or_404(user_id)
            # Roles del usuario vía SQL directo; si falla, listas vacías (evita 500 en prod)
            user_role_ids = _get_user_role_ids(user_id)
            if user_role_ids:
                current_roles = Role.query.filter(Role.id.in_(user_role_ids)).all()
            else:
                current_roles = []
            all_roles = Role.query.filter(Role.code != 'SA').order_by(Role.code).all()
            available_roles = [r for r in all_roles if r.id not in user_role_ids]
            return render_template(
                'admin/users/roles.html',
                user=user,
                current_roles=current_roles,
                available_roles=available_roles,
            )
        except Exception as e:
            db.session.rollback()
            app.logger.exception('admin_user_roles_page error: %s', e)
            flash(f'Error al cargar la página de roles: {str(e)}', 'error')
            return redirect(url_for('admin_users'))


    # ---------------------------------------------------------------------------
    # FASE 4: Consola de Roles y Permisos (solo lectura)
    # ---------------------------------------------------------------------------
    @app.route('/admin/roles')
    @require_permission('roles.view')
    def admin_roles_list():
        """Listado de roles (solo lectura)."""
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_ROLES', 'roles', None,
                'Acceso al listado de roles', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        roles = Role.query.order_by(Role.code).all()
        role_data = []
        for r in roles:
            perm_count = db.session.query(role_permission_table).filter_by(role_id=r.id).count()
            role_data.append({'role': r, 'permission_count': perm_count})
        return render_template('admin/roles/list.html', role_data=role_data)


    @app.route('/admin/roles/<int:role_id>')
    @require_permission('roles.view')
    def admin_roles_detail(role_id):
        """Detalle de un rol con sus permisos (solo lectura)."""
        role = Role.query.get_or_404(role_id)
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_ROLES', 'roles', role_id,
                f'Acceso al detalle del rol {role.code}', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        perms = role.permissions.all()
        return render_template('admin/roles/detail.html', role=role, permissions=perms)


    @app.route('/admin/roles/<int:role_id>/users')
    @require_permission('roles.view')
    def admin_roles_users(role_id):
        """Usuarios que tienen asignado este rol (solo lectura)."""
        role = Role.query.get_or_404(role_id)
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_ROLE_USERS', 'roles', role_id,
                f'Acceso a usuarios del rol {role.code}', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        rows = db.session.execute(
            sql_text('SELECT user_id, assigned_at FROM user_role WHERE role_id = :rid ORDER BY assigned_at DESC'),
            {'rid': role_id}
        ).fetchall()
        users_data = []
        scope_oid = admin_data_scope_organization_id()
        for user_id, assigned_at in rows:
            u = User.query.get(user_id)
            if u and user_has_active_membership(u, int(scope_oid)):
                users_data.append({
                    'user': u,
                    'assigned_at': assigned_at,
                })
        return render_template('admin/roles/users.html', role=role, users_data=users_data)


    @app.route('/admin/permissions')
    @require_permission('roles.view')
    def admin_permissions_list():
        """Listado de permisos del sistema (solo lectura)."""
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_PERMISSIONS', 'permissions', None,
                'Acceso al listado de permisos', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        perms = Permission.query.order_by(Permission.code).all()
        # Categoría desde code (primera parte); roles que tienen cada permiso
        perm_data = []
        for p in perms:
            category = p.code.split('.')[0] if '.' in p.code else 'general'
            roles_with = [r.code for r in p.roles.all()]
            perm_data.append({'permission': p, 'category': category, 'roles': roles_with})
        return render_template('admin/permissions/list.html', perm_data=perm_data)


    @app.route('/api/admin/roles')
    @require_permission('roles.view')
    def api_admin_roles():
        """API: listado de roles con cantidad de permisos."""
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_ROLES', 'roles', None,
                'API: listado de roles', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        roles = Role.query.order_by(Role.code).all()
        out = []
        for r in roles:
            perm_count = db.session.query(role_permission_table).filter_by(role_id=r.id).count()
            out.append({
                'id': r.id, 'code': r.code, 'name': r.name,
                'permissions_count': perm_count,
                'system': (r.code == 'SA'),
            })
        return jsonify(out)


    @app.route('/api/admin/roles/<int:role_id>')
    @require_permission('roles.view')
    def api_admin_roles_detail(role_id):
        """API: detalle de un rol con lista de permisos (códigos)."""
        role = Role.query.get_or_404(role_id)
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_ROLE_DETAIL', 'roles', role_id,
                f'API: detalle rol {role.code}', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        perms = [p.code for p in role.permissions.all()]
        return jsonify({
            'id': role.id, 'code': role.code, 'name': role.name,
            'description': role.description or '',
            'permissions': perms,
            'system': (role.code == 'SA'),
        })


    @app.route('/api/admin/permissions')
    @require_permission('roles.view')
    def api_admin_permissions():
        """API: listado de permisos con categoría (desde code) y roles que los tienen."""
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_PERMISSIONS', 'permissions', None,
                'API: listado de permisos', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        perms = Permission.query.order_by(Permission.code).all()
        out = []
        for p in perms:
            category = p.code.split('.')[0] if '.' in p.code else 'general'
            roles_with = [r.code for r in p.roles.all()]
            out.append({'code': p.code, 'category': category, 'roles': roles_with})
        return jsonify(out)


    @app.route('/api/admin/roles/<int:role_id>/users')
    @require_permission('roles.view')
    def api_admin_roles_users(role_id):
        """API: usuarios que tienen asignado este rol (con assigned_at)."""
        try:
            ActivityLog.log_activity(
                current_user.id, 'VIEW_ROLE_USERS', 'roles', role_id,
                f'API: usuarios por rol', request
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        role = Role.query.get_or_404(role_id)
        rows = db.session.execute(
            sql_text('SELECT user_id, assigned_at FROM user_role WHERE role_id = :rid ORDER BY assigned_at DESC'),
            {'rid': role_id}
        ).fetchall()
        users_data = []
        for user_id, assigned_at in rows:
            u = User.query.get(user_id)
            if u:
                users_data.append({
                    'id': u.id, 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name,
                    'is_active': u.is_active,
                    'assigned_at': assigned_at.isoformat() if assigned_at else None,
                })
        return jsonify({
            'role': {'id': role.id, 'code': role.code, 'name': role.name},
            'users': users_data,
        })
