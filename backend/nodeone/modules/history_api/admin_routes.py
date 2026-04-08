"""Historial de transacciones — rutas de administración (/api/admin/history/*)."""

import csv
import io
import traceback
from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, Response, jsonify, request

# app ya está cargado cuando register_modules importa este módulo
from app import HistoryTransaction, User, admin_data_scope_organization_id, admin_required, db

history_admin_bp = Blueprint('history_admin', __name__, url_prefix='/api/admin/history')


def _scoped_user_ids_subquery():
    from flask_login import current_user
    import app as M

    helper = getattr(M, '_admin_scope_user_ids_only', None)
    if callable(helper):
        return helper()
    scope_oid = admin_data_scope_organization_id()
    q = db.session.query(User.id).filter(User.organization_id == scope_oid)
    try:
        can_view_users = bool(getattr(current_user, 'is_admin', False) or current_user.has_permission('users.view'))
    except Exception:
        can_view_users = bool(getattr(current_user, 'is_admin', False))
    if not can_view_users:
        q = q.filter(User.id == current_user.id)
    return q


@history_admin_bp.route('', methods=['GET'])
@admin_required
def api_admin_get_history():
    """
    API ADMIN: historial de transacciones de todos los usuarios.
    Filtros: user_id, transaction_type, status, start_date, end_date, search, actor_type, visibility.
    """
    try:
        user_id = request.args.get('user_id', type=int)
        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')
        actor_type = request.args.get('actor_type')
        visibility = request.args.get('visibility')

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)

        scoped_user_ids = _scoped_user_ids_subquery()
        query = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id.in_(scoped_user_ids))
            | (HistoryTransaction.actor_id.in_(scoped_user_ids))
        )

        if user_id:
            query = query.filter(
                (HistoryTransaction.owner_user_id == user_id)
                | (HistoryTransaction.actor_id == user_id)
            )

        if transaction_type:
            query = query.filter(HistoryTransaction.transaction_type == transaction_type)

        if status:
            query = query.filter(HistoryTransaction.status == status)

        if actor_type:
            query = query.filter(HistoryTransaction.actor_type == actor_type)

        if visibility:
            query = query.filter(HistoryTransaction.visibility == visibility)

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass

        if search:
            query = query.filter(HistoryTransaction.action.contains(search))

        query = query.order_by(HistoryTransaction.timestamp.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        transactions = []
        for transaction in pagination.items:
            trans_dict = transaction.to_dict(include_sensitive=True)
            if transaction.actor_id:
                actor = User.query.get(transaction.actor_id)
                if actor:
                    trans_dict['actor'] = {
                        'id': actor.id,
                        'email': actor.email,
                        'first_name': actor.first_name,
                        'last_name': actor.last_name,
                    }
            if transaction.owner_user_id:
                owner = User.query.get(transaction.owner_user_id)
                if owner:
                    trans_dict['owner'] = {
                        'id': owner.id,
                        'email': owner.email,
                        'first_name': owner.first_name,
                        'last_name': owner.last_name,
                    }
            transactions.append(trans_dict)

        return jsonify({
            'success': True,
            'transactions': transactions,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
            },
        }), 200

    except Exception as e:
        print(f'❌ Error obteniendo historial admin: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@history_admin_bp.route('/stats', methods=['GET'])
@admin_required
def api_admin_get_history_stats():
    """API ADMIN: estadísticas globales del historial."""
    try:
        user_id = request.args.get('user_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        scoped_user_ids = _scoped_user_ids_subquery()
        query = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id.in_(scoped_user_ids))
            | (HistoryTransaction.actor_id.in_(scoped_user_ids))
        )

        if user_id:
            query = query.filter(
                (HistoryTransaction.owner_user_id == user_id)
                | (HistoryTransaction.actor_id == user_id)
            )

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass

        transactions = query.all()

        total = len(transactions)
        type_counts = Counter(t.transaction_type for t in transactions)
        status_counts = Counter(t.status for t in transactions)
        actor_type_counts = Counter(t.actor_type for t in transactions)

        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)

        recent_7_days = sum(1 for t in transactions if t.timestamp >= week_ago)
        recent_30_days = sum(1 for t in transactions if t.timestamp >= month_ago)

        user_transaction_counts = Counter()
        for t in transactions:
            if t.owner_user_id:
                user_transaction_counts[t.owner_user_id] += 1

        top_users = []
        for uid, count in user_transaction_counts.most_common(10):
            user = User.query.get(uid)
            if user:
                top_users.append({
                    'user_id': uid,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'transaction_count': count,
                })

        errors_recent = sum(
            1 for t in transactions
            if t.transaction_type == 'ERROR' and t.timestamp >= week_ago
        )
        security_recent = sum(
            1 for t in transactions
            if t.transaction_type == 'SECURITY_EVENT' and t.timestamp >= week_ago
        )

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'recent_7_days': recent_7_days,
                'recent_30_days': recent_30_days,
                'by_type': dict(type_counts),
                'by_status': dict(status_counts),
                'by_actor_type': dict(actor_type_counts),
                'errors_recent_7_days': errors_recent,
                'security_events_recent_7_days': security_recent,
                'top_users': top_users,
            },
        }), 200

    except Exception as e:
        print(f'❌ Error obteniendo estadísticas admin de historial: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@history_admin_bp.route('/export', methods=['GET'])
@admin_required
def api_admin_export_history():
    """API ADMIN: exportar historial en CSV."""
    try:
        user_id = request.args.get('user_id', type=int)
        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        scoped_user_ids = _scoped_user_ids_subquery()
        query = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id.in_(scoped_user_ids))
            | (HistoryTransaction.actor_id.in_(scoped_user_ids))
        )

        if user_id:
            query = query.filter(
                (HistoryTransaction.owner_user_id == user_id)
                | (HistoryTransaction.actor_id == user_id)
            )

        if transaction_type:
            query = query.filter(HistoryTransaction.transaction_type == transaction_type)

        if status:
            query = query.filter(HistoryTransaction.status == status)

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(HistoryTransaction.timestamp >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(HistoryTransaction.timestamp <= end_dt)
            except ValueError:
                pass

        transactions = query.order_by(HistoryTransaction.timestamp.desc()).limit(10000).all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'ID', 'UUID', 'Timestamp', 'Transaction Type', 'Actor Type',
            'Actor ID', 'Owner User ID', 'Visibility', 'Action', 'Status',
            'Context App', 'Context Screen', 'Context Module',
        ])

        for t in transactions:
            writer.writerow([
                t.id, t.uuid, t.timestamp.isoformat() if t.timestamp else '',
                t.transaction_type, t.actor_type, t.actor_id or '',
                t.owner_user_id or '', t.visibility, t.action, t.status,
                t.context_app or '', t.context_screen or '', t.context_module or '',
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=history_export.csv'},
        )

    except Exception as e:
        print(f'❌ Error exportando historial: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@history_admin_bp.route('/<int:transaction_id>', methods=['GET'])
@admin_required
def api_admin_get_history_detail(transaction_id):
    """API ADMIN: detalle completo de una transacción."""
    try:
        scoped_user_ids = _scoped_user_ids_subquery()
        transaction = HistoryTransaction.query.filter(
            HistoryTransaction.id == transaction_id,
            (HistoryTransaction.owner_user_id.in_(scoped_user_ids))
            | (HistoryTransaction.actor_id.in_(scoped_user_ids))
        ).first()

        if not transaction:
            return jsonify({'success': False, 'error': 'Transacción no encontrada'}), 404

        trans_dict = transaction.to_dict(include_sensitive=True)

        if transaction.actor_id:
            actor = User.query.get(transaction.actor_id)
            if actor:
                trans_dict['actor'] = {
                    'id': actor.id,
                    'email': actor.email,
                    'first_name': actor.first_name,
                    'last_name': actor.last_name,
                }

        if transaction.owner_user_id:
            owner = User.query.get(transaction.owner_user_id)
            if owner:
                trans_dict['owner'] = {
                    'id': owner.id,
                    'email': owner.email,
                    'first_name': owner.first_name,
                    'last_name': owner.last_name,
                }

        return jsonify({'success': True, 'transaction': trans_dict}), 200

    except Exception as e:
        print(f'❌ Error obteniendo detalle admin de transacción: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
