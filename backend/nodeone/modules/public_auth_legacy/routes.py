"""Registro de rutas public auth/account en app (endpoints legacy)."""

import secrets

import app as M


def register_public_auth_legacy_routes(app):
    from datetime import datetime, timedelta

    from flask import flash, redirect, render_template, request, session, url_for
    from flask_login import current_user, login_required, login_user, logout_user

    from app import db, Membership, SocialAuth, User, VALID_COUNTRIES, validate_cedula_or_passport, validate_country, validate_email_format

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Registro de nuevos usuarios"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            country = request.form.get('country', '').strip()
            cedula_or_passport = request.form.get('cedula_or_passport', '').strip()
        
            # Validar campos obligatorios
            if not email or not password or not first_name or not last_name:
                flash('Todos los campos obligatorios deben ser completados.', 'error')
                return render_template('register.html')
        
            # Validar país
            if country:
                is_valid, error_message = validate_country(country)
                if not is_valid:
                    flash(error_message, 'error')
                    return render_template('register.html')
        
            # Validar cédula o pasaporte
            if cedula_or_passport:
                is_valid, error_message = validate_cedula_or_passport(cedula_or_passport, country)
                if not is_valid:
                    flash(error_message, 'error')
                    return render_template('register.html')
        
            # Validar formato de email
            is_valid, error_message = validate_email_format(email)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('register.html')
        
            # Verificar si el usuario ya existe
            if User.query.filter_by(email=email.lower()).first():
                flash('El correo electrónico ya está registrado.', 'error')
                return render_template('register.html')
        
            # Crear nuevo usuario (empresa: subdominio, form saas_organization_id o default)
            user = User(
                email=email.lower(),
                first_name=first_name,
                last_name=last_name,
                phone=phone if phone else None,
                country=country if country else None,
                cedula_or_passport=cedula_or_passport if cedula_or_passport else None,
                organization_id=M._organization_id_for_public_registration(),
            )
            user.set_password(password)
            user.email_verified = False
        
            db.session.add(user)
            db.session.commit()  # Commit inicial para obtener el ID del usuario

            # Asignar membresía básica al registrarse para que pueda emitir certificado de membresía desde el primer día
            try:
                end_date = datetime.utcnow() + timedelta(days=365)
                free_membership = Membership(
                    user_id=user.id,
                    membership_type='basic',
                    start_date=datetime.utcnow(),
                    end_date=end_date,
                    is_active=True,
                    payment_status='paid',
                    amount=0.0
                )
                db.session.add(free_membership)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                pass  # No romper el registro si falla (ej. tabla Membership no existe aún)

            # Registrar registro de usuario en historial
            try:
                from history_module import HistoryLogger
                HistoryLogger.log_user_action(
                    user_id=user.id,
                    action="Registro de nuevo usuario",
                    status="success",
                    context={"app": "web", "screen": "register", "module": "auth"},
                    payload={"email": email, "first_name": first_name, "last_name": last_name},
                    result={"user_id": user.id},
                    request=request
                )
            except Exception as e:
                pass  # No romper el flujo si falla el historial

            # Automatización marketing: member_created
            try:
                from _app.modules.marketing.service import trigger_automation
                base_url = request.host_url.rstrip('/') if request else None
                trigger_automation('member_created', user.id, base_url=base_url)
            except Exception:
                pass

            # Enviar email de verificación (genera el token y hace commit)
            try:
                M.apply_email_config_from_db()
                ok, err_detail = M.send_verification_email(user)
                if not ok and err_detail:
                    print(f"❌ Verificación no enviada: {err_detail}")
            except Exception as e:
                print(f"❌ Error enviando email de verificación: {e}")
                import traceback
                traceback.print_exc()
        
            # Enviar notificación de bienvenida (solo si el email se envió correctamente)
            try:
                M.NotificationEngine.notify_welcome(user)
            except Exception as e:
                print(f"❌ Error enviando notificación de bienvenida: {e}")
        
            flash('Registro exitoso. Por favor, verifica tu email para acceder a todas las funciones. Revisa tu bandeja de entrada (y spam).', 'success')
            return redirect(url_for('auth.login'))
    
        return render_template('register.html', valid_countries=VALID_COUNTRIES)

    @app.route('/verify-email/<token>')
    def verify_email(token):
        """Verificar email con token"""
        try:
            # Buscar usuario con el token (sin importar si está verificado o no)
            user = User.query.filter_by(email_verification_token=token).first()
        
            if not user:
                print(f"❌ Token de verificación no encontrado: {token[:20]}...")
                flash('El enlace de verificación no es válido. Por favor, solicita uno nuevo.', 'error')
                return redirect(url_for('auth.login'))
        
            print(f"🔍 Verificando email para usuario: {user.email} (ID: {user.id})")
            print(f"   Token expira: {user.email_verification_token_expires}")
            print(f"   Hora actual: {datetime.utcnow()}")
            print(f"   Ya verificado: {user.email_verified}")
        
            # Si ya está verificado, permitir acceso pero informar
            if user.email_verified:
                flash('Tu email ya está verificado. Puedes iniciar sesión normalmente.', 'info')
                if current_user.is_authenticated and current_user.id == user.id:
                    return redirect(url_for('dashboard'))
                return redirect(url_for('auth.login'))
        
            # Verificar si el token expiró
            if user.email_verification_token_expires:
                time_diff = (user.email_verification_token_expires - datetime.utcnow()).total_seconds()
                print(f"   Tiempo restante: {time_diff} segundos")
            
                if time_diff <= 0:
                    print(f"❌ Token expirado para usuario {user.email}")
                    flash('El enlace de verificación ha expirado. Por favor, solicita uno nuevo.', 'error')
                    return redirect(url_for('resend_verification'))
        
            # Verificar email
            user.email_verified = True
            user.email_verification_token = None
            user.email_verification_token_expires = None
            db.session.commit()
        
            print(f"✅ Email verificado exitosamente para {user.email}")
            flash('¡Email verificado exitosamente! Ahora puedes iniciar sesión y acceder a todas las funciones.', 'success')
        
            # Si el usuario no está logueado, redirigir al login con mensaje claro
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
        
            # Si está logueado pero es otro usuario, cerrar sesión y redirigir
            if current_user.id != user.id:
                logout_user()
                flash('Por favor, inicia sesión con tu cuenta.', 'info')
                return redirect(url_for('auth.login'))
        
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            print(f"❌ Error en verify_email: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            flash('Ocurrió un error al verificar tu email. Por favor, intenta nuevamente o solicita un nuevo enlace.', 'error')
            return redirect(url_for('auth.login'))

    @app.route('/resend-verification', methods=['GET', 'POST'])
    @login_required
    def resend_verification():
        """Reenviar email de verificación"""
        if request.method == 'POST':
            if current_user.email_verified:
                flash('Tu email ya está verificado.', 'info')
                return redirect(url_for('dashboard'))
        
            try:
                M.apply_email_config_from_db()
                ok, err_detail = M.send_verification_email(current_user)
                if ok:
                    flash('Email de verificación reenviado. Revisa tu bandeja de entrada (y spam).', 'success')
                else:
                    msg = 'Error al enviar el email de verificación. Por favor, intenta más tarde.'
                    if err_detail:
                        msg += ' ' + (err_detail[:250] + '…' if len(err_detail) > 250 else err_detail)
                    flash(msg, 'error')
            except Exception as e:
                flash('Error al reenviar el email de verificación: ' + str(e)[:200], 'error')
                print(f"❌ Error reenviando verificación: {e}")
        
            return redirect(url_for('dashboard'))
    
        # Si es GET, mostrar página simple para reenviar
        if current_user.email_verified:
            return redirect(url_for('dashboard'))
    
        return render_template('resend_verification.html')

    @app.route('/auth/<provider>/callback')
    def oauth_callback(provider):
        """Callback OAuth: intercambia código por token, obtiene userinfo, crea/vincula usuario y hace login."""
        if not M.OAUTH_AVAILABLE or provider not in ('google', 'facebook', 'linkedin'):
            flash('Login social no disponible para este proveedor.', 'error')
            return redirect(url_for('auth.login'))
        try:
            client = getattr(M.oauth, provider)
            token = client.authorize_access_token()
            # Google/OpenID: userinfo suele venir en token['userinfo']; Facebook/LinkedIN a veces hay que pedirlo
            userinfo = token.get('userinfo')
            if not userinfo and provider in ('facebook', 'linkedin'):
                ep = {
                    'facebook': 'https://graph.facebook.com/v18.0/me?fields=id,name,email,first_name,last_name',
                    'linkedin': 'https://api.linkedin.com/v2/userinfo',
                }
                resp = client.get(ep[provider], token=token)
                if resp and getattr(resp, 'status_code', 0) == 200:
                    raw = resp.json()
                    if provider == 'facebook':
                        userinfo = {
                            'sub': str(raw.get('id', '')),
                            'email': raw.get('email', ''),
                            'name': raw.get('name', ''),
                            'given_name': raw.get('first_name', ''),
                            'family_name': raw.get('last_name', ''),
                        }
                    else:
                        userinfo = raw
            if not userinfo:
                flash('No se pudo obtener la información del perfil.', 'error')
                return redirect(url_for('auth.login'))
            # Normalizar campos (OpenID: sub, email, name, given_name, family_name)
            sub = userinfo.get('sub') or userinfo.get('id') or ''
            email = (userinfo.get('email') or '').strip().lower()
            if not email:
                flash('El proveedor no compartió tu correo. Usa el registro con email.', 'error')
                return redirect(url_for('auth.login'))
            name = userinfo.get('name') or ''
            given_name = userinfo.get('given_name') or name.split(None, 1)[0] if name else ''
            family_name = userinfo.get('family_name') or (name.split(None, 1)[1] if len(name.split(None, 1)) > 1 else '')
            provider_user_id = str(sub)
            # Buscar por SocialAuth o por email
            social = SocialAuth.query.filter_by(provider=provider, provider_user_id=provider_user_id).first()
            if social:
                user = User.query.get(social.user_id)
            else:
                user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    first_name=given_name or 'Usuario',
                    last_name=family_name or 'Social',
                    phone=None,
                    country=None,
                    cedula_or_passport=None,
                organization_id=M._organization_id_for_public_registration(),
                )
                user.set_password(secrets.token_urlsafe(32))
                user.email_verified = True
                db.session.add(user)
                db.session.flush()
                link = SocialAuth(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
                db.session.add(link)
                db.session.commit()
            else:
                social_existing = SocialAuth.query.filter_by(user_id=user.id, provider=provider).first()
                if not social_existing:
                    link = SocialAuth(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
                    db.session.add(link)
                    db.session.commit()
            if not user.is_active:
                flash('Tu cuenta está desactivada.', 'error')
                return redirect(url_for('auth.login'))
            login_user(user)
            ok_oauth_org, oauth_org_err = M.apply_session_organization_after_login(user, request)
            if not ok_oauth_org:
                logout_user()
                flash(oauth_org_err or 'No se pudo validar la organización.', 'error')
                return redirect(url_for('auth.login'))
            if bool(getattr(user, 'must_change_password', False)):
                flash('Debes cambiar tu contraseña antes de continuar.', 'warning')
                return redirect(url_for('auth.change_password'))
            from _app.modules.auth.service import safe_next_path
            next_page = (
                safe_next_path(session.pop('oauth_post_login_next', None))
                or safe_next_path(request.args.get('next'))
            )
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        except Exception as e:
            print(f"❌ OAuth callback error ({provider}): {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            flash('Error al iniciar sesión con el proveedor. Intenta de nuevo o usa email/contraseña.', 'error')
            return redirect(url_for('auth.login'))


    @app.route('/auth/<provider>')
    def oauth_login(provider):
        """Redirige al proveedor OAuth (Google, Facebook, LinkedIn)."""
        if not M.OAUTH_AVAILABLE or provider not in ('google', 'facebook', 'linkedin'):
            flash('Login social no disponible.', 'error')
            return redirect(url_for('auth.login'))
        client = getattr(M.oauth, provider, None)
        if not client or not app.config.get(f'{provider.upper()}_CLIENT_ID'):
            flash(f'Login con {provider.capitalize()} no está configurado.', 'error')
            return redirect(url_for('auth.login'))
        from _app.modules.auth.service import safe_next_path
        session.pop('oauth_post_login_next', None)
        n = safe_next_path(request.args.get('next'))
        if n:
            session['oauth_post_login_next'] = n
        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        return client.authorize_redirect(redirect_uri)


    @app.route('/logout')
    @login_required
    def logout():
        """Cerrar sesión"""
        # Registrar logout en historial
        try:
            from history_module import HistoryLogger
            HistoryLogger.log_user_action(
                user_id=current_user.id,
                action="Logout",
                status="success",
                context={"app": "web", "screen": "logout", "module": "auth"},
                request=request
            )
        except Exception as e:
            pass  # No romper el flujo si falla el historial

        logout_user()
        flash('Has cerrado sesión exitosamente.', 'info')
        return redirect(url_for('index'))

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """Solicitar recuperación de contraseña"""
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
        
            if not email:
                flash('Por favor, ingresa tu correo electrónico.', 'error')
                return render_template('forgot_password.html')
        
            # Buscar usuario por email
            user = User.query.filter_by(email=email).first()
        
            # Por seguridad, siempre mostrar mensaje de éxito aunque el email no exista
            # Esto previene enumeración de usuarios
            if user and user.is_active:
                # Generar token de recuperación
                reset_token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=1)  # Válido por 1 hora
            
                # Guardar token en la base de datos
                user.password_reset_token = reset_token
                user.password_reset_token_expires = expires_at
                user.password_reset_sent_at = datetime.utcnow()
                db.session.commit()
            
                # Generar URL de recuperación
                reset_url = f"{request.url_root.rstrip('/')}/reset-password?token={reset_token}"
            
                # Enviar email de recuperación
                try:
                    if M.EMAIL_TEMPLATES_AVAILABLE and M.email_service:
                        html_content = M.get_password_reset_email(user, reset_token, reset_url)
                        M.email_service.send_email(
                            to_email=user.email,
                            subject='Restablecer Contraseña - RelaticPanama',
                            html_content=html_content,
                            email_type='password_reset',
                            recipient_id=user.id,
                            recipient_email=user.email,
                            recipient_name=f"{user.first_name} {user.last_name}"
                        )
                        flash('Se ha enviado un enlace de recuperación a tu correo electrónico. Revisa tu bandeja de entrada y carpeta de spam.', 'success')
                    else:
                        flash('Error: El servicio de email no está disponible. Contacta al administrador.', 'error')
                except Exception as e:
                    print(f"Error enviando email de recuperación: {e}")
                    flash('Error al enviar el email. Por favor, intenta nuevamente o contacta al soporte.', 'error')
            else:
                # Mostrar mensaje genérico para no revelar si el email existe
                flash('Si el correo electrónico existe en nuestro sistema, recibirás un enlace de recuperación.', 'info')
    
        return render_template('forgot_password.html')

    @app.route('/reset-password', methods=['GET', 'POST'])
    def reset_password():
        """Restablecer contraseña con token"""
        token = request.args.get('token') or request.form.get('token')
    
        if not token:
            flash('Token de recuperación no válido o faltante.', 'error')
            return redirect(url_for('forgot_password'))
    
        # Buscar usuario con token válido
        user = User.query.filter_by(password_reset_token=token).first()
    
        if not user:
            flash('Token de recuperación no válido o expirado.', 'error')
            return redirect(url_for('forgot_password'))
    
        # Verificar que el token no haya expirado
        if user.password_reset_token_expires and user.password_reset_token_expires < datetime.utcnow():
            flash('El enlace de recuperación ha expirado. Por favor, solicita uno nuevo.', 'error')
            # Limpiar token expirado
            user.password_reset_token = None
            user.password_reset_token_expires = None
            db.session.commit()
            return redirect(url_for('forgot_password'))
    
        if request.method == 'POST':
            new_password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
        
            # Validaciones
            if not new_password:
                flash('Por favor, ingresa una nueva contraseña.', 'error')
                return render_template('reset_password.html', token=token, user=user)
        
            if len(new_password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres.', 'error')
                return render_template('reset_password.html', token=token, user=user)
        
            if new_password != confirm_password:
                flash('Las contraseñas no coinciden.', 'error')
                return render_template('reset_password.html', token=token, user=user)
        
            # Actualizar contraseña
            user.set_password(new_password)
        
            # Limpiar token de recuperación
            user.password_reset_token = None
            user.password_reset_token_expires = None
            user.password_reset_sent_at = None
        
            db.session.commit()
        
            # Registrar en historial
            try:
                from history_module import HistoryLogger
                HistoryLogger.log_user_action(
                    user_id=user.id,
                    action="Contraseña restablecida",
                    status="success",
                    context={"app": "web", "screen": "reset_password", "module": "auth"},
                    request=request
                )
            except Exception as e:
                pass
        
            flash('Tu contraseña ha sido restablecida exitosamente. Puedes iniciar sesión ahora.', 'success')
            return redirect(url_for('auth.login'))
    
        return render_template('reset_password.html', token=token, user=user)

