#!/usr/bin/env python3
"""
Módulo de Historial de Transacciones
Proporciona métodos para registrar todas las transacciones y eventos del sistema
"""

import json
from datetime import datetime
from flask import request as flask_request


class HistoryLogger:
    """
    Logger para registrar transacciones en el historial
    Todos los métodos son estáticos para facilitar el uso
    """
    
    @staticmethod
    def _extract_metadata(request=None):
        """
        Extraer metadata del request Flask
        Retorna diccionario con IP, user_agent, session_id
        """
        if not request:
            try:
                from flask import request as flask_request
                request = flask_request
            except RuntimeError:
                # Fuera de contexto de request
                request = None
        
        metadata = {
            'ip': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None,
            'session_id': None  # Se puede obtener de session si es necesario
        }
        
        # Intentar obtener session_id si está disponible
        try:
            from flask import session
            if hasattr(session, 'get'):
                metadata['session_id'] = session.get('session_id')
        except:
            pass
        
        return metadata
    
    @staticmethod
    def _create_transaction(transaction_type, actor_type, actor_id, 
                           owner_user_id, visibility, action, status,
                           context=None, payload=None, result=None, 
                           request=None):
        """
        Método interno para crear registro de transacción
        No debe romper el flujo principal si hay errores
        """
        try:
            from app import HistoryTransaction, db
            import uuid as uuid_lib
            
            # Extraer metadata
            metadata = HistoryLogger._extract_metadata(request)
            
            # Crear transacción
            transaction = HistoryTransaction(
                uuid=str(uuid_lib.uuid4()),
                transaction_type=transaction_type,
                actor_type=actor_type,
                actor_id=actor_id,
                owner_user_id=owner_user_id,
                visibility=visibility,
                action=action,
                status=status,
                context_app=context.get('app') if context else None,
                context_screen=context.get('screen') if context else None,
                context_module=context.get('module') if context else None,
                payload=json.dumps(payload) if payload else None,
                result=json.dumps(result) if result else None,
                transaction_metadata=json.dumps(metadata) if metadata else None
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return transaction
        except Exception as e:
            # No debe romper el flujo principal
            print(f"⚠️ Error registrando historial: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return None
    
    @staticmethod
    def log_user_action(user_id, action, status='success', 
                       context=None, payload=None, result=None, 
                       request=None, visibility='both'):
        """
        Registrar acción de usuario
        
        Args:
            user_id: ID del usuario que ejecutó la acción
            action: Descripción de la acción (ej: "Login exitoso")
            status: Estado de la acción ('pending', 'success', 'failed', 'cancelled')
            context: Diccionario con 'app', 'screen', 'module'
            payload: Datos de entrada (será serializado a JSON)
            result: Resultado de la acción (será serializado a JSON)
            request: Objeto request de Flask (opcional, se obtiene automáticamente)
            visibility: 'admin', 'user', o 'both'
        
        Returns:
            HistoryTransaction o None si hay error
        """
        return HistoryLogger._create_transaction(
            transaction_type='USER_ACTION',
            actor_type='user',
            actor_id=user_id,
            owner_user_id=user_id,
            visibility=visibility,
            action=action,
            status=status,
            context=context,
            payload=payload,
            result=result,
            request=request
        )
    
    @staticmethod
    def log_system_action(action, status='success', context=None, 
                         payload=None, result=None, owner_user_id=None,
                         visibility='admin'):
        """
        Registrar acción del sistema
        
        Args:
            action: Descripción de la acción (ej: "Webhook recibido")
            status: Estado de la acción
            context: Diccionario con 'app', 'screen', 'module'
            payload: Datos de entrada
            result: Resultado de la acción
            owner_user_id: ID del usuario relacionado (opcional)
            visibility: 'admin', 'user', o 'both'
        
        Returns:
            HistoryTransaction o None si hay error
        """
        return HistoryLogger._create_transaction(
            transaction_type='SYSTEM_ACTION',
            actor_type='system',
            actor_id=None,
            owner_user_id=owner_user_id,
            visibility=visibility,
            action=action,
            status=status,
            context=context,
            payload=payload,
            result=result,
            request=None
        )
    
    @staticmethod
    def log_error(error_type, error_message, context=None, user_id=None,
                 request=None, payload=None):
        """
        Registrar error del sistema
        
        Args:
            error_type: Tipo de error (ej: "PaymentError", "ValidationError")
            error_message: Mensaje del error
            context: Diccionario con contexto
            user_id: ID del usuario si el error está relacionado con uno
            request: Objeto request de Flask
            payload: Datos relacionados al error
        
        Returns:
            HistoryTransaction o None si hay error
        """
        return HistoryLogger._create_transaction(
            transaction_type='ERROR',
            actor_type='user' if user_id else 'system',
            actor_id=user_id,
            owner_user_id=user_id,
            visibility='both',
            action=f"Error: {error_type}",
            status='failed',
            context=context,
            payload=payload,
            result={'error': str(error_message)},
            request=request
        )
    
    @staticmethod
    def log_security_event(event_type, user_id, context=None, 
                          request=None, payload=None):
        """
        Registrar evento de seguridad
        
        Args:
            event_type: Tipo de evento (ej: "Login fallido", "Acceso no autorizado")
            user_id: ID del usuario relacionado (None si es sistema)
            context: Diccionario con contexto
            request: Objeto request de Flask
            payload: Datos relacionados al evento
        
        Returns:
            HistoryTransaction o None si hay error
        """
        return HistoryLogger._create_transaction(
            transaction_type='SECURITY_EVENT',
            actor_type='user' if user_id else 'system',
            actor_id=user_id,
            owner_user_id=user_id,
            visibility='admin',
            action=f"Security: {event_type}",
            status='success',
            context=context,
            payload=payload,
            result=None,
            request=request
        )
    
    @staticmethod
    def log_info(message, context=None, user_id=None, request=None):
        """
        Registrar información general
        
        Args:
            message: Mensaje informativo
            context: Diccionario con contexto
            user_id: ID del usuario si aplica
            request: Objeto request de Flask
        
        Returns:
            HistoryTransaction o None si hay error
        """
        return HistoryLogger._create_transaction(
            transaction_type='INFO',
            actor_type='user' if user_id else 'system',
            actor_id=user_id,
            owner_user_id=user_id,
            visibility='both',
            action=message,
            status='success',
            context=context,
            payload=None,
            result=None,
            request=request
        )
    
    @staticmethod
    def log_warning(message, context=None, user_id=None, request=None, payload=None):
        """
        Registrar advertencia
        
        Args:
            message: Mensaje de advertencia
            context: Diccionario con contexto
            user_id: ID del usuario si aplica
            request: Objeto request de Flask
            payload: Datos relacionados
        
        Returns:
            HistoryTransaction o None si hay error
        """
        return HistoryLogger._create_transaction(
            transaction_type='WARNING',
            actor_type='user' if user_id else 'system',
            actor_id=user_id,
            owner_user_id=user_id,
            visibility='both',
            action=f"Warning: {message}",
            status='success',
            context=context,
            payload=payload,
            result=None,
            request=request
        )
