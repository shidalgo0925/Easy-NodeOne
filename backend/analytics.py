#!/usr/bin/env python3
"""
Módulo de Analytics y Reportes
Proporciona funcionalidades para análisis de datos, reportes personalizables y exportación
"""

from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, extract, and_, or_
from sqlalchemy.orm import Session
import json


class AnalyticsService:
    """Servicio para análisis de datos y métricas"""
    
    def __init__(self, db_session, models=None):
        self.db = db_session
        # Usar modelos pasados como parámetro o importarlos dinámicamente
        if models:
            self.User = models.get('User')
            self.Subscription = models.get('Subscription')
            self.Payment = models.get('Payment')
            self.Event = models.get('Event')
            self.EventRegistration = models.get('EventRegistration')
            self.MembershipPricing = models.get('MembershipPricing')
        else:
            # Importar dinámicamente para evitar importaciones circulares
            import sys
            if 'app' in sys.modules:
                app_module = sys.modules['app']
                self.User = getattr(app_module, 'User', None)
                self.Subscription = getattr(app_module, 'Subscription', None)
                self.Payment = getattr(app_module, 'Payment', None)
                self.Event = getattr(app_module, 'Event', None)
                self.EventRegistration = getattr(app_module, 'EventRegistration', None)
                self.MembershipPricing = getattr(app_module, 'MembershipPricing', None)
    
    def get_user_metrics(self, start_date=None, end_date=None):
        """Obtener métricas de usuarios"""
        query = self.db.query(self.User)
        
        if start_date:
            query = query.filter(self.User.created_at >= start_date)
        if end_date:
            query = query.filter(self.User.created_at <= end_date)
        
        total_users = query.count()
        
        # Usuarios activos (con membresía activa)
        active_users = self.db.query(self.User).join(self.Subscription).filter(
            self.Subscription.status == 'active'
        ).distinct().count()
        
        # Nuevos usuarios en el período
        if start_date and end_date:
            new_users = query.filter(
                self.User.created_at >= start_date,
                self.User.created_at <= end_date
            ).count()
        else:
            new_users = query.filter(
                self.User.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
        
        # Usuarios por país
        users_by_country = self.db.query(
            self.User.country,
            func.count(self.User.id).label('count')
        ).group_by(self.User.country).all()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users': new_users,
            'users_by_country': {country: count for country, count in users_by_country if country}
        }
    
    def get_membership_metrics(self, start_date=None, end_date=None):
        """Obtener métricas de membresías"""
        query = self.db.query(self.Subscription)
        
        if start_date:
            query = query.filter(self.Subscription.created_at >= start_date)
        if end_date:
            query = query.filter(self.Subscription.created_at <= end_date)
        
        # Membresías por tipo
        memberships_by_type = self.db.query(
            self.Subscription.membership_type,
            func.count(self.Subscription.id).label('count')
        ).group_by(self.Subscription.membership_type).all()
        
        # Membresías activas
        active_memberships = query.filter(self.Subscription.status == 'active').count()
        
        # Membresías expiradas
        expired_memberships = query.filter(self.Subscription.status == 'expired').count()
        
        # Membresías pausadas
        paused_memberships = query.filter(self.Subscription.is_paused == True).count()
        
        # Nuevas membresías en el período
        if start_date and end_date:
            new_memberships = query.filter(
                self.Subscription.created_at >= start_date,
                self.Subscription.created_at <= end_date
            ).count()
        else:
            new_memberships = query.filter(
                self.Subscription.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
        
        return {
            'total_memberships': query.count(),
            'active_memberships': active_memberships,
            'expired_memberships': expired_memberships,
            'paused_memberships': paused_memberships,
            'new_memberships': new_memberships,
            'by_type': {mtype: count for mtype, count in memberships_by_type}
        }
    
    def get_payment_metrics(self, start_date=None, end_date=None):
        """Obtener métricas de pagos"""
        query = self.db.query(self.Payment)
        
        if start_date:
            query = query.filter(self.Payment.created_at >= start_date)
        if end_date:
            query = query.filter(self.Payment.created_at <= end_date)
        
        # Total de ingresos
        total_revenue = query.filter(self.Payment.status == 'succeeded').with_entities(
            func.sum(self.Payment.amount)
        ).scalar() or 0
        
        # Pagos por método
        payments_by_method = self.db.query(
            self.Payment.payment_method,
            func.count(self.Payment.id).label('count'),
            func.sum(self.Payment.amount).label('total')
        ).filter(self.Payment.status == 'succeeded').group_by(self.Payment.payment_method).all()
        
        # Pagos por estado
        payments_by_status = self.db.query(
            self.Payment.status,
            func.count(self.Payment.id).label('count')
        ).group_by(self.Payment.status).all()
        
        # Pagos por mes
        monthly_payments = self.db.query(
            extract('year', self.Payment.created_at).label('year'),
            extract('month', self.Payment.created_at).label('month'),
            func.count(self.Payment.id).label('count'),
            func.sum(self.Payment.amount).label('total')
        ).filter(
            self.Payment.status == 'succeeded',
            self.Payment.created_at >= datetime.utcnow() - timedelta(days=365)
        ).group_by(
            extract('year', self.Payment.created_at),
            extract('month', self.Payment.created_at)
        ).order_by('year', 'month').all()
        
        return {
            'total_revenue': total_revenue / 100.0,  # Convertir de centavos a dólares
            'total_payments': query.count(),
            'successful_payments': query.filter(self.Payment.status == 'succeeded').count(),
            'by_method': {method: {'count': count, 'total': total/100.0} 
                         for method, count, total in payments_by_method},
            'by_status': {status: count for status, count in payments_by_status},
            'monthly_trend': [
                {
                    'month': f"{int(year)}-{int(month):02d}",
                    'count': int(count),
                    'total': float(total/100.0) if total else 0
                }
                for year, month, count, total in monthly_payments
            ]
        }
    
    def get_event_metrics(self, start_date=None, end_date=None):
        """Obtener métricas de eventos"""
        query = self.db.query(self.Event)
        
        if start_date:
            query = query.filter(self.Event.created_at >= start_date)
        if end_date:
            query = query.filter(self.Event.created_at <= end_date)
        
        # Eventos por estado
        events_by_status = self.db.query(
            self.Event.publish_status,
            func.count(self.Event.id).label('count')
        ).group_by(self.Event.publish_status).all()
        
        # Registros a eventos
        total_registrations = self.db.query(self.EventRegistration).count()
        
        # Eventos más populares
        popular_events = self.db.query(
            self.Event.id,
            self.Event.title,
            func.count(self.EventRegistration.id).label('registrations')
        ).join(self.EventRegistration, self.Event.id == self.EventRegistration.event_id).group_by(
            self.Event.id, self.Event.title
        ).order_by(func.count(self.EventRegistration.id).desc()).limit(10).all()
        
        return {
            'total_events': query.count(),
            'by_status': {status: count for status, count in events_by_status},
            'total_registrations': total_registrations,
            'popular_events': [
                {'id': eid, 'title': title, 'registrations': regs}
                for eid, title, regs in popular_events
            ]
        }
    
    def get_comprehensive_metrics(self, start_date=None, end_date=None):
        """Obtener todas las métricas en un solo objeto"""
        return {
            'users': self.get_user_metrics(start_date, end_date),
            'memberships': self.get_membership_metrics(start_date, end_date),
            'payments': self.get_payment_metrics(start_date, end_date),
            'events': self.get_event_metrics(start_date, end_date),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            }
        }
    
    def get_realtime_metrics(self):
        """Obtener métricas en tiempo real (últimas 24 horas)"""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        return {
            'timestamp': now.isoformat(),
            'last_24h': {
                'new_users': self.get_user_metrics(last_24h, now)['new_users'],
                'new_memberships': self.get_membership_metrics(last_24h, now)['new_memberships'],
                'new_payments': self.get_payment_metrics(last_24h, now)['total_payments'],
                'revenue_24h': self.get_payment_metrics(last_24h, now)['total_revenue']
            }
        }

