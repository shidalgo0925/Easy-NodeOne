#!/usr/bin/env python3
"""
Rutas y vistas para la gestión de eventos, descuentos y su consumo desde el
panel administrativo, el portal de miembros y APIs públicas.
"""

from datetime import datetime, timedelta
import os
import re
import unicodedata

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from functools import wraps

# Decorador admin_required
def admin_required(f):
    """Decorador para requerir permisos de administrador"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            from flask import flash, redirect, url_for
            flash('No tienes permisos para acceder a esta página.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Inicializar referencias a modelos dinámicamente para evitar importaciones
# circulares con app.py
db = None
Event = None
EventImage = None
Discount = None
EventDiscount = None
ActivityLog = None
allowed_file = None


def init_models():
    """Importa los modelos necesarios desde app.py una vez que existen."""
    global db, Event, EventImage, Discount, EventDiscount, ActivityLog, allowed_file, EventRegistration, NotificationEngine, User
    try:
        from app import (
            db as _db,
            Event as _Event,
            EventImage as _EventImage,
            Discount as _Discount,
            EventDiscount as _EventDiscount,
            ActivityLog as _ActivityLog,
            allowed_file as _allowed_file,
            EventRegistration as _EventRegistration,
            NotificationEngine as _NotificationEngine,
            User as _User,
        )

        db = _db
        Event = _Event
        EventImage = _EventImage
        Discount = _Discount
        EventDiscount = _EventDiscount
        ActivityLog = _ActivityLog
        allowed_file = _allowed_file
        EventRegistration = _EventRegistration
        NotificationEngine = _NotificationEngine
        User = _User
    except ImportError:
        pass


def ensure_models():
    """Garantiza que los modelos estén inicializados antes de usarlos."""
    if Event is None:
        init_models()


def _slugify(value: str) -> str:
    """Genera un slug URL-safe basado en el título."""
    value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return value or f"evento-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def _unique_slug(base_slug: str, event_id=None) -> str:
    ensure_models()
    slug = base_slug
    counter = 1
    while True:
        query = Event.query.filter(Event.slug == slug)
        if event_id:
            query = query.filter(Event.id != event_id)
        exists = db.session.query(query.exists()).scalar()
        if not exists:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def _parse_datetime(field_name: str):
    value = request.form.get(field_name, '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        return None


def _uploads_dir():
    folder = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'events')
    os.makedirs(folder, exist_ok=True)
    return folder


def _remove_file_if_exists(path):
    if not path:
        return
    absolute = os.path.join(current_app.root_path, '..', path.lstrip('/'))
    if os.path.exists(absolute):
        try:
            os.remove(absolute)
        except OSError:
            pass


def _save_file(storage, prefix='event'):
    if not storage or storage.filename == '' or not allowed_file(storage.filename):
        return None
    filename = secure_filename(storage.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    new_name = f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.{ext}"
    storage.save(os.path.join(_uploads_dir(), new_name))
    return f"/static/uploads/events/{new_name}"


def _serialize_event(event, membership_type=None):
    data = {
        'id': event.id,
        'slug': event.slug,
        'title': event.title,
        'summary': event.summary,
        'description': event.description,
        'category': event.category,
        'format': event.format,
        'tags': event.tags,
        'currency': event.currency,
        'start_date': event.start_date.isoformat() if event.start_date else None,
        'end_date': event.end_date.isoformat() if event.end_date else None,
        'registration_deadline': event.registration_deadline.isoformat() if event.registration_deadline else None,
        'cover_image': event.cover_url(),
        'is_virtual': event.is_virtual,
        'location': event.location,
        'country': event.country,
        'has_certificate': event.has_certificate,
        'certificate_instructions': event.certificate_instructions,
        'visibility': event.visibility,
        'publish_status': event.publish_status,
        'featured': event.featured,
    }
    pricing = event.pricing_for_membership(membership_type)
    data['pricing'] = {
        'base_price': pricing['base_price'],
        'final_price': pricing['final_price'],
        'discount': {
            'name': pricing['discount'].name,
            'value': pricing['discount'].value,
            'type': pricing['discount'].discount_type,
            'membership_tier': pricing['discount'].membership_tier,
        } if pricing['discount'] else None
    }
    return data


# Blueprints
events_bp = Blueprint('events', __name__, url_prefix='/events')
admin_events_bp = Blueprint('admin_events', __name__, url_prefix='/admin/events')
events_api_bp = Blueprint('events_api', __name__, url_prefix='/api/events')


# ------------------------------------------------------------------------------
# Portal de miembros
# ------------------------------------------------------------------------------
@events_bp.route('/')
@login_required
def list_events():
    ensure_models()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None
    status = request.args.get('status', 'published')
    category = request.args.get('category', '').strip()
    search = request.args.get('q', '').strip()

    query = Event.query
    if status != 'all':
        query = query.filter(Event.publish_status == status)
    if category:
        query = query.filter(Event.category == category)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Event.title.ilike(like), Event.summary.ilike(like), Event.tags.ilike(like)))

    events = query.order_by(Event.start_date.asc()).all()
    categories = sorted({evt.category for evt in events if evt.category})

    return render_template(
        'events/list.html',
        events=events,
        categories=categories,
        active_category=category,
        search=search,
        status=status,
        membership=membership,
        membership_type=membership_type
    )


@events_bp.route('/<string:slug>')
@login_required
def event_detail(slug):
    ensure_models()
    event = Event.query.filter_by(slug=slug).first_or_404()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None
    pricing = event.pricing_for_membership(membership_type)
    
    # Verificar si el usuario ya está registrado
    registration = EventRegistration.query.filter_by(
        event_id=event.id,
        user_id=current_user.id
    ).first() if EventRegistration else None
    
    # Verificar capacidad disponible
    is_full = False
    available_spots = None
    if event.capacity and event.capacity > 0:
        registered_count = EventRegistration.query.filter_by(
            event_id=event.id,
            registration_status='confirmed'
        ).count() if EventRegistration else 0
        available_spots = event.capacity - registered_count
        is_full = available_spots <= 0
    
    return render_template(
        'events/detail.html',
        event=event,
        membership=membership,
        pricing=pricing,
        registration=registration,
        is_full=is_full,
        available_spots=available_spots
    )


@events_bp.route('/<string:slug>/register', methods=['POST'])
@login_required
def register_to_event(slug):
    """Registrar usuario a un evento - Agrega al carrito si tiene precio, registra directamente si es gratis"""
    # Verificar que el email esté verificado
    if not current_user.email_verified:
        flash('Debes verificar tu email para registrarte en eventos. Revisa tu bandeja de entrada o solicita un nuevo enlace de verificación.', 'warning')
        return redirect(url_for('resend_verification'))
    
    ensure_models()
    event = Event.query.filter_by(slug=slug).first_or_404()
    membership = current_user.get_active_membership()
    membership_type = membership.membership_type if membership else None
    
    # Verificar si ya está registrado
    existing_registration = EventRegistration.query.filter_by(
        event_id=event.id,
        user_id=current_user.id
    ).first() if EventRegistration else None
    
    if existing_registration:
        flash('Ya estás registrado en este evento.', 'info')
        return redirect(url_for('events.event_detail', slug=slug))
    
    # Verificar capacidad
    if event.capacity and event.capacity > 0:
        registered_count = EventRegistration.query.filter_by(
            event_id=event.id,
            registration_status='confirmed'
        ).count() if EventRegistration else 0
        if registered_count >= event.capacity:
            flash('Lo sentimos, este evento ya está lleno.', 'error')
            return redirect(url_for('events.event_detail', slug=slug))
    
    # Calcular precio con descuentos
    pricing = event.pricing_for_membership(membership_type)
    base_price = pricing['base_price']
    final_price = pricing['final_price']
    discount_applied = base_price - final_price
    
    # Si el evento es GRATIS (precio = 0), registrar directamente sin pasar por carrito
    if final_price == 0:
        # Crear registro directamente para eventos gratis
        registration = EventRegistration(
            event_id=event.id,
            user_id=current_user.id,
            base_price=base_price,
            final_price=final_price,
            discount_applied=discount_applied,
            membership_type=membership_type,
            registration_status='confirmed'  # Confirmado automáticamente si es gratis
        )
        
        db.session.add(registration)
        
        # Actualizar contador de registrados
        if event.registered_count is None:
            event.registered_count = 0
        event.registered_count += 1
        
        # Log de actividad
        ActivityLog.log_activity(
            current_user.id,
            'register_event',
            'event',
            event.id,
            f'Usuario registrado al evento (gratis): {event.title}',
            request
        )
        
        db.session.commit()
        
        # Notificar al responsable del evento
        if NotificationEngine:
            NotificationEngine.notify_event_registration(event, current_user, registration)
        
        flash('Te has registrado exitosamente al evento. Recibirás un email de confirmación.', 'success')
        return redirect(url_for('events.event_detail', slug=slug))
    
    # Si el evento tiene precio, AGREGAR AL CARRITO
    else:
        # Importar funciones del carrito desde app.py
        from app import add_to_cart, get_or_create_cart
        
        # Verificar si el evento ya está en el carrito
        cart = get_or_create_cart(current_user.id)
        from app import CartItem
        import json
        
        existing_cart_item = CartItem.query.filter_by(
            cart_id=cart.id,
            product_type='event',
            product_id=event.id
        ).first()
        
        if existing_cart_item:
            flash('Este evento ya está en tu carrito de compras.', 'info')
            return redirect(url_for('cart'))
        
        # Agregar evento al carrito
        metadata = {
            'event_id': event.id,
            'event_slug': event.slug,
            'base_price': base_price,
            'final_price': final_price,
            'discount_applied': discount_applied,
            'membership_type': membership_type
        }
        
        add_to_cart(
            user_id=current_user.id,
            product_type='event',
            product_id=event.id,
            product_name=event.title,
            unit_price=int(final_price * 100),  # Convertir a centavos
            quantity=1,
            product_description=event.summary or (event.description[:200] if event.description else ""),
            metadata=metadata
        )
        
        # Log de actividad
        ActivityLog.log_activity(
            current_user.id,
            'add_event_to_cart',
            'event',
            event.id,
            f'Evento agregado al carrito: {event.title}',
            request
        )
        
        flash('Evento agregado al carrito. Completa el pago para confirmar tu registro.', 'success')
        return redirect(url_for('cart'))


@events_bp.route('/<string:slug>/cancel-registration', methods=['POST'])
@login_required
def cancel_event_registration(slug):
    """Cancelar registro a un evento"""
    ensure_models()
    event = Event.query.filter_by(slug=slug).first_or_404()
    registration = EventRegistration.query.filter_by(
        event_id=event.id,
        user_id=current_user.id
    ).first_or_404() if EventRegistration else None
    
    if not registration:
        flash('No tienes un registro activo para este evento.', 'error')
        return redirect(url_for('events.event_detail', slug=slug))
    
    registration.registration_status = 'cancelled'
    
    # Actualizar contador
    if event.registered_count and event.registered_count > 0:
        event.registered_count -= 1
    
    # Log de actividad
    ActivityLog.log_activity(
        current_user.id,
        'cancel_event_registration',
        'event',
        event.id,
        f'Registro cancelado al evento: {event.title}',
        request
    )
    
    db.session.commit()
    
    # Notificar al responsable del evento
    if NotificationEngine:
        NotificationEngine.notify_event_cancellation(event, current_user, registration)
    
    flash('Tu registro al evento ha sido cancelado.', 'info')
    return redirect(url_for('events.event_detail', slug=slug))


@admin_events_bp.route('/<int:event_id>/registrations/<int:registration_id>/confirm', methods=['POST'])
@admin_required
def confirm_event_registration(event_id, registration_id):
    """Confirmar un registro pendiente a un evento"""
    print(f"🔍 confirm_event_registration llamado - event_id: {event_id}, registration_id: {registration_id}")
    ensure_models()
    event = Event.query.get_or_404(event_id)
    registration = EventRegistration.query.get_or_404(registration_id)
    user = registration.user
    
    print(f"📋 Registro encontrado - Estado actual: {registration.registration_status}, Usuario: {user.email}")
    
    if registration.event_id != event.id:
        flash('El registro no corresponde a este evento.', 'error')
        return redirect(url_for('admin_events.admin_events_index'))
    
    # Confirmar el registro PRIMERO y hacer commit inmediatamente
    old_status = registration.registration_status
    registration.registration_status = 'confirmed'
    print(f"✅ Estado cambiado de '{old_status}' a 'confirmed'")
    
    # Log de actividad
    ActivityLog.log_activity(
        current_user.id,
        'confirm_event_registration',
        'event',
        event.id,
        f'Registro confirmado: {user.first_name} {user.last_name} - {event.title}',
        request
    )
    
    # Hacer commit INMEDIATAMENTE para guardar el cambio de estado
    try:
        db.session.commit()
        print(f"✅ Commit exitoso. Estado cambiado a 'confirmed' para usuario {user.email}")
        
        # Refrescar para obtener el estado actualizado
        db.session.refresh(registration)
        print(f"🔍 Verificación post-commit - Estado: {registration.registration_status}")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error haciendo commit del estado: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error al confirmar el registro: {str(e)}', 'error')
        return redirect(request.referrer or url_for('admin_events.admin_events_index'))
    
    # DESPUÉS del commit, enviar emails (si fallan, el registro ya está confirmado)
    # Enviar email de confirmación al usuario usando EmailService
    try:
        from app import EmailService, log_email_sent
        from email_templates import get_event_registration_email
        email_service = EmailService()
        
        # Usar template de email si está disponible
        try:
            email_template = get_event_registration_email(event, user, registration)
            html_content = email_template
            text_content = None  # El template ya incluye todo
        except:
            # Fallback si el template no está disponible
            html_content = f"""
            <h2>¡Registro Confirmado!</h2>
            <p>Hola {user.first_name},</p>
            <p>Tu registro al evento <strong>{event.title}</strong> ha sido confirmado.</p>
            <p><strong>Detalles del evento:</strong></p>
            <ul>
                <li><strong>Fecha:</strong> {event.start_date.strftime('%d/%m/%Y %H:%M')} - {event.end_date.strftime('%d/%m/%Y %H:%M')}</li>
                <li><strong>Ubicación:</strong> {event.location or ('Virtual' if event.is_virtual else 'Por definir')}</li>
                <li><strong>Precio pagado:</strong> ${registration.final_price:.2f} {event.currency}</li>
            </ul>
            <p>Te esperamos en el evento. Si tienes alguna pregunta, no dudes en contactarnos.</p>
            <p>Saludos,<br>Equipo RelaticPanama</p>
            """
            text_content = None
        
        # Enviar email usando EmailService (que registra automáticamente en EmailLog)
        email_sent = email_service.send_email(
            subject=f'[RelaticPanama] Registro confirmado: {event.title}',
            recipients=[user.email],
            html_content=html_content,
            text_content=text_content,
            email_type='event_confirmation',
            related_entity_type='event',
            related_entity_id=event.id,
            recipient_id=user.id,
            recipient_name=f"{user.first_name} {user.last_name}"
        )
        
        if email_sent:
            registration.confirmation_email_sent = True
            registration.confirmation_email_sent_at = datetime.utcnow()
            db.session.commit()  # Guardar el flag de email enviado
            print(f"✅ Email de confirmación enviado a {user.email} para evento {event.id}")
        else:
            print(f"❌ Error enviando email de confirmación a {user.email}")
            registration.confirmation_email_sent = False
            try:
                db.session.commit()  # Guardar el flag aunque haya fallado
            except:
                pass
            
    except Exception as e:
        print(f"❌ Error enviando email de confirmación: {e}")
        import traceback
        traceback.print_exc()
        registration.confirmation_email_sent = False
        try:
            db.session.commit()  # Guardar el flag aunque haya fallado
        except:
            pass
    
    # Notificar al responsable del evento (después de confirmar el registro)
    if NotificationEngine:
        print(f"📧 Enviando notificaciones a responsables del evento...")
        try:
            NotificationEngine.notify_event_confirmation(event, user, registration)
        except Exception as e:
            print(f"⚠️ Error en notificaciones (no afecta la confirmación): {e}")
    
    flash(f'Registro de {user.first_name} {user.last_name} confirmado exitosamente.', 'success')
    return redirect(request.referrer or url_for('admin_events.admin_events_index'))


@admin_events_bp.route('/<int:event_id>/registrations/<int:registration_id>/delete', methods=['POST'])
@admin_required
def delete_event_registration(event_id, registration_id):
    """Eliminar completamente un registro de participante de un evento"""
    ensure_models()
    event = Event.query.get_or_404(event_id)
    registration = EventRegistration.query.get_or_404(registration_id)
    user = registration.user
    
    if registration.event_id != event.id:
        flash('El registro no corresponde a este evento.', 'error')
        return redirect(url_for('admin_events.admin_events_index'))
    
    # Guardar información para el log
    user_name = f"{user.first_name} {user.last_name}"
    user_email = user.email
    was_confirmed = registration.registration_status == 'confirmed'
    
    # Actualizar contador si el registro estaba confirmado
    if was_confirmed and event.registered_count and event.registered_count > 0:
        event.registered_count -= 1
    
    # Eliminar el registro
    db.session.delete(registration)
    
    # Log de actividad
    ActivityLog.log_activity(
        current_user.id,
        'delete_event_registration',
        'event',
        event.id,
        f'Registro eliminado: {user_name} ({user_email}) - {event.title}',
        request
    )
    
    db.session.commit()
    flash(f'Registro de {user_name} eliminado exitosamente.', 'info')
    return redirect(url_for('admin_events.event_registrations', event_id=event.id))


# ------------------------------------------------------------------------------
# API pública
# ------------------------------------------------------------------------------
@events_api_bp.route('/', methods=['GET'])
def api_events():
    ensure_models()
    status = request.args.get('status', 'published')
    limit = request.args.get('limit', type=int)
    membership_type = request.args.get('membership_type')

    query = Event.query
    if status != 'all':
        query = query.filter(Event.publish_status == status)
    query = query.order_by(Event.start_date.asc())
    if limit:
        query = query.limit(limit)

    events = query.all()
    return jsonify({'events': [_serialize_event(evt, membership_type) for evt in events]})


@events_api_bp.route('/<string:slug>', methods=['GET'])
def api_event_detail(slug):
    ensure_models()
    event = Event.query.filter_by(slug=slug).first_or_404()
    membership_type = request.args.get('membership_type')
    return jsonify({'event': _serialize_event(event, membership_type)})


# ------------------------------------------------------------------------------
# Panel Administrativo - Eventos
# ------------------------------------------------------------------------------
@admin_events_bp.route('/')
@admin_required
def admin_events_index():
    ensure_models()
    status = request.args.get('status', 'all')
    category = request.args.get('category', '').strip()

    query = Event.query
    if status != 'all':
        query = query.filter(Event.publish_status == status)
    if category:
        query = query.filter(Event.category == category)

    events = query.order_by(Event.start_date.desc()).all()
    stats = {
        'total': Event.query.count(),
        'published': Event.query.filter_by(publish_status='published').count(),
        'drafts': Event.query.filter_by(publish_status='draft').count(),
        'archived': Event.query.filter_by(publish_status='archived').count(),
    }

    return render_template(
        'admin/events/list.html',
        events=events,
        status=status,
        category=category,
        stats=stats
    )


@admin_events_bp.route('/<int:event_id>/registrations')
@admin_required
def event_registrations(event_id):
    """Vista para ver y gestionar registros de un evento"""
    ensure_models()
    event = Event.query.get_or_404(event_id)
    
    # Verificar que el usuario sea responsable del evento (creador, moderador, administrador o expositor)
    is_responsible = (
        event.created_by == current_user.id or
        event.moderator_id == current_user.id or
        event.administrator_id == current_user.id or
        event.speaker_id == current_user.id or
        current_user.is_admin
    )
    
    if not is_responsible:
        flash('No tienes permisos para ver los registros de este evento.', 'error')
        return redirect(url_for('admin_events.admin_events_index'))
    
    status_filter = request.args.get('status', 'all')
    query = EventRegistration.query.filter_by(event_id=event.id)
    
    if status_filter != 'all':
        query = query.filter_by(registration_status=status_filter)
    
    registrations = query.order_by(EventRegistration.registration_date.desc()).all()
    
    stats = {
        'total': EventRegistration.query.filter_by(event_id=event.id).count(),
        'pending': EventRegistration.query.filter_by(event_id=event.id, registration_status='pending').count(),
        'confirmed': EventRegistration.query.filter_by(event_id=event.id, registration_status='confirmed').count(),
        'cancelled': EventRegistration.query.filter_by(event_id=event.id, registration_status='cancelled').count(),
    }
    
    return render_template(
        'admin/events/registrations.html',
        event=event,
        registrations=registrations,
        status_filter=status_filter,
        stats=stats
    )


@admin_events_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_event():
    ensure_models()
    discounts = Discount.query.order_by(Discount.name.asc()).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('El título es obligatorio.', 'error')
            return redirect(request.url)

        slug = request.form.get('slug', '').strip() or _slugify(title)
        slug = _unique_slug(slug)

        start_date = _parse_datetime('start_date')
        end_date = _parse_datetime('end_date')
        if not start_date or not end_date:
            flash('Las fechas de inicio y fin son obligatorias.', 'error')
            return redirect(request.url)
        if end_date <= start_date:
            flash('La fecha de fin debe ser posterior a la de inicio.', 'error')
            return redirect(request.url)

        event = Event(
            title=title,
            slug=slug,
            summary=request.form.get('summary', '').strip(),
            description=request.form.get('description', '').strip(),
            category=request.form.get('category', 'general').strip() or 'general',
            format=request.form.get('format', 'virtual').strip() or 'virtual',
            tags=request.form.get('tags', '').strip(),
            base_price=request.form.get('base_price', type=float) or 0.0,
            currency=request.form.get('currency', 'USD').upper(),
            registration_url=request.form.get('registration_url', '').strip(),
            contact_email=request.form.get('contact_email', '').strip(),
            contact_phone=request.form.get('contact_phone', '').strip(),
            location=request.form.get('location', '').strip(),
            country=request.form.get('country', '').strip(),
            is_virtual=bool(request.form.get('is_virtual')),
            has_certificate=bool(request.form.get('has_certificate')),
            certificate_instructions=request.form.get('certificate_instructions', '').strip(),
            capacity=request.form.get('capacity', type=int) or 0,
            visibility=request.form.get('visibility', 'members'),
            publish_status=request.form.get('publish_status', 'draft'),
            featured=bool(request.form.get('featured')),
            start_date=start_date,
            end_date=end_date,
            registration_deadline=_parse_datetime('registration_deadline'),
            created_by=current_user.id,
            moderator_id=request.form.get('moderator_id', type=int) or None,
            administrator_id=request.form.get('administrator_id', type=int) or None,
            speaker_id=request.form.get('speaker_id', type=int) or None
        )

        db.session.add(event)
        db.session.flush()

        cover_path = _save_file(request.files.get('cover_image'), prefix='cover')
        if cover_path:
            event.cover_image = cover_path

        gallery_files = request.files.getlist('gallery_images')
        for idx, file in enumerate(gallery_files):
            path = _save_file(file, prefix='gallery')
            if path:
                db.session.add(EventImage(
                    event_id=event.id,
                    file_path=path,
                    sort_order=idx,
                    is_primary=False
                ))

        selected_discounts = request.form.getlist('discount_ids')
        for order, discount_id in enumerate(selected_discounts, start=1):
            try:
                discount = Discount.query.get(int(discount_id))
            except (TypeError, ValueError):
                discount = None
            if discount:
                db.session.add(EventDiscount(
                    event_id=event.id,
                    discount_id=discount.id,
                    priority=order
                ))

        db.session.commit()
        ActivityLog.log_activity(
            current_user.id,
            'create_event',
            'event',
            event.id,
            f'Evento creado: {event.title}',
            request
        )
        flash('Evento creado correctamente.', 'success')
        return redirect(url_for('admin_events.admin_events_index'))

    default_start = (datetime.utcnow() + timedelta(days=7)).replace(minute=0, second=0, microsecond=0)
    default_end = default_start + timedelta(hours=2)
    users = User.query.order_by(User.first_name, User.last_name).all() if User else []
    return render_template(
        'admin/events/form.html',
        action='create',
        event=None,
        discounts=discounts,
        users=users,
        default_start=default_start,
        default_end=default_end
    )


@admin_events_bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_event(event_id):
    ensure_models()
    event = Event.query.get_or_404(event_id)
    discounts = Discount.query.order_by(Discount.name.asc()).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('El título es obligatorio.', 'error')
            return redirect(request.url)

        slug = request.form.get('slug', '').strip() or _slugify(title)
        event.slug = _unique_slug(slug, event_id=event.id)

        start_date = _parse_datetime('start_date')
        end_date = _parse_datetime('end_date')
        if not start_date or not end_date:
            flash('Las fechas de inicio y fin son obligatorias.', 'error')
            return redirect(request.url)
        if end_date <= start_date:
            flash('La fecha de fin debe ser posterior a la de inicio.', 'error')
            return redirect(request.url)

        event.title = title
        event.summary = request.form.get('summary', '').strip()
        event.description = request.form.get('description', '').strip()
        event.category = request.form.get('category', 'general').strip() or 'general'
        event.format = request.form.get('format', 'virtual').strip() or 'virtual'
        event.tags = request.form.get('tags', '').strip()
        event.base_price = request.form.get('base_price', type=float) or 0.0
        event.currency = request.form.get('currency', 'USD').upper()
        event.registration_url = request.form.get('registration_url', '').strip()
        event.contact_email = request.form.get('contact_email', '').strip()
        event.contact_phone = request.form.get('contact_phone', '').strip()
        event.location = request.form.get('location', '').strip()
        event.country = request.form.get('country', '').strip()
        event.is_virtual = bool(request.form.get('is_virtual'))
        event.has_certificate = bool(request.form.get('has_certificate'))
        event.certificate_instructions = request.form.get('certificate_instructions', '').strip()
        event.capacity = request.form.get('capacity', type=int) or 0
        event.visibility = request.form.get('visibility', 'members')
        event.publish_status = request.form.get('publish_status', 'draft')
        event.featured = bool(request.form.get('featured'))
        event.start_date = start_date
        event.end_date = end_date
        event.registration_deadline = _parse_datetime('registration_deadline')
        event.moderator_id = request.form.get('moderator_id', type=int) or None
        event.administrator_id = request.form.get('administrator_id', type=int) or None
        event.speaker_id = request.form.get('speaker_id', type=int) or None

        if request.form.get('remove_cover'):
            _remove_file_if_exists(event.cover_image)
            event.cover_image = None

        new_cover = _save_file(request.files.get('cover_image'), prefix='cover')
        if new_cover:
            _remove_file_if_exists(event.cover_image)
            event.cover_image = new_cover

        delete_ids = request.form.getlist('delete_images')
        for image_id in delete_ids:
            image = EventImage.query.filter_by(id=image_id, event_id=event.id).first()
            if image:
                _remove_file_if_exists(image.file_path)
                db.session.delete(image)

        current_order = len(event.images)
        gallery_files = request.files.getlist('gallery_images')
        for idx, file in enumerate(gallery_files):
            path = _save_file(file, prefix='gallery')
            if path:
                db.session.add(EventImage(
                    event_id=event.id,
                    file_path=path,
                    sort_order=current_order + idx,
                    is_primary=False
                ))

        EventDiscount.query.filter_by(event_id=event.id).delete()
        selected_discounts = request.form.getlist('discount_ids')
        for order, discount_id in enumerate(selected_discounts, start=1):
            try:
                discount = Discount.query.get(int(discount_id))
            except (TypeError, ValueError):
                discount = None
            if discount:
                db.session.add(EventDiscount(
                    event_id=event.id,
                    discount_id=discount.id,
                    priority=order
                ))

        db.session.commit()
        ActivityLog.log_activity(
            current_user.id,
            'update_event',
            'event',
            event.id,
            f'Evento actualizado: {event.title}',
            request
        )
        
        # Notificar sobre la actualización del evento
        if NotificationEngine:
            NotificationEngine.notify_event_update(event)
        
        flash('Evento actualizado correctamente.', 'success')
        return redirect(url_for('admin_events.admin_events_index'))

    users = User.query.order_by(User.first_name, User.last_name).all() if User else []
    return render_template(
        'admin/events/form.html',
        action='edit',
        event=event,
        discounts=discounts,
        users=users,
        default_start=event.start_date,
        default_end=event.end_date
    )


@admin_events_bp.route('/<int:event_id>/duplicate', methods=['POST'])
@admin_required
def duplicate_event(event_id):
    """Duplicar evento"""
    ensure_models()
    original = Event.query.get_or_404(event_id)
    
    try:
        # Crear copia del evento
        duplicate = Event(
            title=f"{original.title} (Copia)",
            slug=_unique_slug(_slugify(f"{original.title} (Copia)")),
            summary=original.summary,
            description=original.description,
            category=original.category,
            format=original.format,
            tags=original.tags,
            base_price=original.base_price,
            currency=original.currency,
            location=original.location,
            virtual_link=original.virtual_link,
            capacity=original.capacity,
            publish_status='draft',  # Por defecto borrador
            featured=False,  # No destacar por defecto
            start_date=original.start_date,
            end_date=original.end_date,
            registration_deadline=original.registration_deadline,
            created_by=current_user.id,
            moderator_id=original.moderator_id,
            administrator_id=original.administrator_id,
            speaker_id=original.speaker_id
        )
        
        db.session.add(duplicate)
        db.session.flush()  # Para obtener el ID del duplicado
        
        # Copiar imagen de portada si existe
        if original.cover_image:
            duplicate.cover_image = original.cover_image
        
        # Copiar imágenes de galería
        for original_image in original.gallery_images:
            db.session.add(EventImage(
                event_id=duplicate.id,
                file_path=original_image.file_path,
                sort_order=original_image.sort_order,
                is_primary=original_image.is_primary
            ))
        
        # Copiar descuentos asociados
        for event_discount in original.discounts:
            db.session.add(EventDiscount(
                event_id=duplicate.id,
                discount_id=event_discount.discount_id,
                priority=event_discount.priority
            ))
        
        db.session.commit()
        
        ActivityLog.log_activity(
            current_user.id,
            'duplicate_event',
            'event',
            duplicate.id,
            f'Evento duplicado desde: {original.title}',
            request
        )
        
        flash(f'Evento "{original.title}" duplicado exitosamente.', 'success')
        return redirect(url_for('admin_events.edit_event', event_id=duplicate.id))
    except Exception as e:
        db.session.rollback()
        print(f"Error duplicando evento: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error al duplicar evento: {str(e)}', 'error')
        return redirect(url_for('admin_events.admin_events_index'))

@admin_events_bp.route('/<int:event_id>/delete', methods=['POST'])
@admin_required
def delete_event(event_id):
    ensure_models()
    event = Event.query.get_or_404(event_id)
    title = event.title

    _remove_file_if_exists(event.cover_image)
    for image in event.images:
        _remove_file_if_exists(image.file_path)

    db.session.delete(event)
    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'delete_event',
        'event',
        event_id,
        f'Evento eliminado: {title}',
        request
    )
    flash('Evento eliminado correctamente.', 'info')
    return redirect(url_for('admin_events.admin_events_index'))


# ------------------------------------------------------------------------------
# Panel Administrativo - Descuentos
# ------------------------------------------------------------------------------
@admin_events_bp.route('/discounts')
@admin_required
def discounts_index():
    ensure_models()
    discounts = Discount.query.order_by(Discount.created_at.desc()).all()
    return render_template('admin/events/discount_list.html', discounts=discounts)


@admin_events_bp.route('/discounts/create', methods=['GET', 'POST'])
@admin_required
def create_discount():
    ensure_models()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('El nombre es obligatorio.', 'error')
            return redirect(request.url)

        discount = Discount(
            name=name,
            code=request.form.get('code', '').strip() or None,
            description=request.form.get('description', '').strip(),
            discount_type=request.form.get('discount_type', 'percentage'),
            value=request.form.get('value', type=float) or 0.0,
            membership_tier=request.form.get('membership_tier', '').strip() or None,
            category=request.form.get('category', 'event'),
            applies_automatically='applies_automatically' in request.form,
            is_active='is_active' in request.form,
            max_uses=request.form.get('max_uses', type=int),
            start_date=_parse_datetime('start_date'),
            end_date=_parse_datetime('end_date')
        )
        db.session.add(discount)
        db.session.commit()

        ActivityLog.log_activity(
            current_user.id,
            'create_discount',
            'discount',
            discount.id,
            f'Descuento creado: {discount.name}',
            request
        )
        flash('Descuento creado correctamente.', 'success')
        return redirect(url_for('admin_events.discounts_index'))

    return render_template('admin/events/discount_form.html', action='create', discount=None)


@admin_events_bp.route('/discounts/<int:discount_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_discount(discount_id):
    ensure_models()
    discount = Discount.query.get_or_404(discount_id)

    if request.method == 'POST':
        discount.name = request.form.get('name', '').strip()
        discount.code = request.form.get('code', '').strip() or None
        discount.description = request.form.get('description', '').strip()
        discount.discount_type = request.form.get('discount_type', 'percentage')
        discount.value = request.form.get('value', type=float) or 0.0
        discount.membership_tier = request.form.get('membership_tier', '').strip() or None
        discount.category = request.form.get('category', 'event')
        discount.applies_automatically = 'applies_automatically' in request.form
        discount.is_active = 'is_active' in request.form
        discount.max_uses = request.form.get('max_uses', type=int)
        discount.start_date = _parse_datetime('start_date')
        discount.end_date = _parse_datetime('end_date')

        db.session.commit()
        ActivityLog.log_activity(
            current_user.id,
            'update_discount',
            'discount',
            discount.id,
            f'Descuento actualizado: {discount.name}',
            request
        )
        flash('Descuento actualizado correctamente.', 'success')
        return redirect(url_for('admin_events.discounts_index'))

    return render_template('admin/events/discount_form.html', action='edit', discount=discount)


@admin_events_bp.route('/discounts/<int:discount_id>/delete', methods=['POST'])
@admin_required
def delete_discount(discount_id):
    ensure_models()
    discount = Discount.query.get_or_404(discount_id)
    name = discount.name
    db.session.delete(discount)
    db.session.commit()

    ActivityLog.log_activity(
        current_user.id,
        'delete_discount',
        'discount',
        discount_id,
        f'Descuento eliminado: {name}',
        request
    )
    flash('Descuento eliminado.', 'info')
    return redirect(url_for('admin_events.discounts_index'))
