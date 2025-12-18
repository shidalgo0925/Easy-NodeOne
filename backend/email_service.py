#!/usr/bin/env python3
"""
Servicio de envío de correos electrónicos para RelaticPanama
Maneja el envío de correos con reintentos y manejo de errores
"""

import logging
from flask_mail import Message
from datetime import datetime
from functools import wraps
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:
    """Servicio centralizado para envío de correos electrónicos"""
    
    def __init__(self, mail_instance, max_retries=3, retry_delay=2):
        """
        Inicializar el servicio de correo
        
        Args:
            mail_instance: Instancia de Flask-Mail
            max_retries: Número máximo de reintentos
            retry_delay: Segundos de espera entre reintentos
        """
        self.mail = mail_instance
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def send_email(self, subject, recipients, html_content, text_content=None, sender=None, 
                   email_type=None, related_entity_type=None, related_entity_id=None, 
                   recipient_id=None, recipient_name=None):
        """
        Enviar correo electrónico con reintentos automáticos y registro en EmailLog
        
        Args:
            subject: Asunto del correo
            recipients: Lista de destinatarios o string único
            html_content: Contenido HTML del correo
            text_content: Contenido de texto plano (opcional)
            sender: Remitente (opcional, usa el configurado por defecto)
            email_type: Tipo de email (membership_payment, event_registration, etc.)
            related_entity_type: Tipo de entidad relacionada (membership, event, etc.)
            related_entity_id: ID de la entidad relacionada
            recipient_id: ID del usuario destinatario (opcional)
            recipient_name: Nombre del destinatario (opcional)
        
        Returns:
            bool: True si se envió exitosamente, False en caso contrario
        """
        if isinstance(recipients, str):
            recipients = [recipients]
        
        # Importar modelos aquí para evitar import circular
        try:
            from app import db, EmailLog, User
        except ImportError:
            EmailLog = None
            db = None
        
        last_error = None
        
        # Obtener remitente por defecto si no se especifica
        if not sender:
            sender = self.mail.app.config.get('MAIL_DEFAULT_SENDER', 'noreply@relaticpanama.org') if hasattr(self.mail, 'app') else 'noreply@relaticpanama.org'
        
        for attempt in range(self.max_retries):
            try:
                msg = Message(
                    subject=subject,
                    recipients=recipients,
                    html=html_content,
                    body=text_content,
                    sender=sender
                )
                
                self.mail.send(msg)
                logger.info(f"Email enviado exitosamente a {recipients} - Asunto: {subject}")
                
                # Registrar en EmailLog si está disponible
                if EmailLog and db:
                    try:
                        for recipient_email in recipients:
                            # Obtener información del destinatario si es usuario del sistema
                            user = None
                            if recipient_id:
                                user = User.query.get(recipient_id)
                            elif not recipient_id:
                                user = User.query.filter_by(email=recipient_email).first()
                            
                            # Obtener remitente de la configuración
                            from_email = sender or (self.mail.app.config.get('MAIL_DEFAULT_SENDER', 'noreply@relaticpanama.org') if hasattr(self.mail, 'app') else 'noreply@relaticpanama.org')
                            
                            # Crear diccionario con datos del email log
                            email_log_data = {
                                'from_email': from_email,
                                'recipient_id': user.id if user else None,
                                'recipient_email': recipient_email,
                                'recipient_name': recipient_name or (f"{user.first_name} {user.last_name}" if user else recipient_email),
                                'subject': subject,
                                'html_content': html_content[:5000],  # Limitar tamaño
                                'text_content': text_content[:5000] if text_content else None,
                                'email_type': email_type or 'general',
                                'related_entity_type': related_entity_type,
                                'related_entity_id': related_entity_id,
                                'status': 'sent',
                                'retry_count': attempt,
                                'sent_at': datetime.utcnow()
                            }
                            
                            # Si la tabla tiene to_email, agregarlo
                            from sqlalchemy import inspect
                            inspector = inspect(db.engine)
                            columns = [c['name'] for c in inspector.get_columns('email_log')]
                            if 'to_email' in columns:
                                email_log_data['to_email'] = recipient_email
                            
                            email_log = EmailLog(**email_log_data)
                            db.session.add(email_log)
                        db.session.commit()
                    except Exception as log_error:
                        logger.error(f"Error registrando email en log: {log_error}")
                        if db:
                            db.session.rollback()
                
                return True
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Error enviando email (intento {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Backoff exponencial
                else:
                    logger.error(f"Falló el envío de email después de {self.max_retries} intentos")
                    
                    # Registrar fallo en EmailLog
                    if EmailLog and db:
                        try:
                            for recipient_email in recipients:
                                user = None
                                if recipient_id:
                                    user = User.query.get(recipient_id)
                                elif not recipient_id:
                                    user = User.query.filter_by(email=recipient_email).first()
                                
                                # Obtener remitente de la configuración
                                from_email = sender or (self.mail.app.config.get('MAIL_DEFAULT_SENDER', 'noreply@relaticpanama.org') if hasattr(self.mail, 'app') else 'noreply@relaticpanama.org')
                                
                                # Crear diccionario con datos del email log
                                email_log_data = {
                                    'from_email': from_email,
                                    'recipient_id': user.id if user else None,
                                    'recipient_email': recipient_email,
                                    'recipient_name': recipient_name or (f"{user.first_name} {user.last_name}" if user else recipient_email),
                                    'subject': subject,
                                    'html_content': html_content[:5000],
                                    'text_content': text_content[:5000] if text_content else None,
                                    'email_type': email_type or 'general',
                                    'related_entity_type': related_entity_type,
                                    'related_entity_id': related_entity_id,
                                    'status': 'failed',
                                    'error_message': last_error[:1000],  # Limitar tamaño
                                    'retry_count': attempt + 1,
                                    'sent_at': None
                                }
                                
                                # Si la tabla tiene to_email, agregarlo
                                from sqlalchemy import inspect
                                inspector = inspect(db.engine)
                                columns = [c['name'] for c in inspector.get_columns('email_log')]
                                if 'to_email' in columns:
                                    email_log_data['to_email'] = recipient_email
                                
                                email_log = EmailLog(**email_log_data)
                                db.session.add(email_log)
                            db.session.commit()
                        except Exception as log_error:
                            logger.error(f"Error registrando email fallido en log: {log_error}")
                            if db:
                                db.session.rollback()
                    
                    return False
        
        return False
    
    def send_bulk_email(self, emails_data):
        """
        Enviar múltiples correos electrónicos
        
        Args:
            emails_data: Lista de diccionarios con keys: subject, recipients, html_content, text_content
        
        Returns:
            dict: Estadísticas de envío {'success': int, 'failed': int, 'total': int}
        """
        stats = {'success': 0, 'failed': 0, 'total': len(emails_data)}
        
        for email_data in emails_data:
            success = self.send_email(
                subject=email_data.get('subject'),
                recipients=email_data.get('recipients'),
                html_content=email_data.get('html_content'),
                text_content=email_data.get('text_content'),
                sender=email_data.get('sender')
            )
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Enviados {stats['success']}/{stats['total']} correos exitosamente")
        return stats
    
    def send_template_email(self, template_func, *args, **kwargs):
        """
        Enviar correo usando una función de plantilla
        
        Args:
            template_func: Función que retorna el HTML del correo
            *args, **kwargs: Argumentos para la función de plantilla
        
        Returns:
            bool: True si se envió exitosamente
        """
        try:
            html_content = template_func(*args, **kwargs)
            # Extraer el subject del HTML si es posible, o usar uno por defecto
            subject = kwargs.get('subject', 'Notificación de RelaticPanama')
            
            recipients = kwargs.get('recipients')
            if not recipients:
                # Intentar obtener del primer argumento si es un usuario
                if args and hasattr(args[0], 'email'):
                    recipients = args[0].email
                else:
                    logger.error("No se especificaron destinatarios")
                    return False
            
            return self.send_email(
                subject=subject,
                recipients=recipients,
                html_content=html_content
            )
        except Exception as e:
            logger.error(f"Error enviando correo con plantilla: {e}")
            return False


def email_with_logging(func):
    """Decorador para logging de envíos de correo"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"{func.__name__} ejecutado en {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error en {func.__name__} después de {elapsed:.2f}s: {e}")
            raise
    return wrapper

