"""Historial de transacciones — rutas de miembro (/api/history/*)."""

import traceback
from collections import Counter
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

history_member_bp = Blueprint('history_member', __name__, url_prefix='/api/history')


@history_member_bp.route('', methods=['GET'])
@login_required
def api_get_history():
    """
    API endpoint para obtener historial de transacciones del usuario.
    Filtros: transaction_type, status, start_date, end_date; paginación: page, per_page.
    """
    try:
        from app import HistoryTransaction

        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        query = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id == current_user.id)
            | (HistoryTransaction.visibility.in_(['user', 'both']))
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

        if search:
            query = query.filter(HistoryTransaction.action.contains(search))

        query = query.order_by(HistoryTransaction.timestamp.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        transactions = []
        for transaction in pagination.items:
            transactions.append(transaction.to_dict(include_sensitive=False))

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
        print(f'❌ Error obteniendo historial: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@history_member_bp.route('/<int:transaction_id>', methods=['GET'])
@login_required
def api_get_history_detail(transaction_id):
    """API endpoint para obtener detalles de una transacción específica."""
    try:
        from app import HistoryTransaction

        transaction = HistoryTransaction.query.filter_by(id=transaction_id).first()

        if not transaction:
            return jsonify({'success': False, 'error': 'Transacción no encontrada'}), 404

        if transaction.owner_user_id != current_user.id and transaction.visibility not in ['user', 'both']:
            return jsonify({'success': False, 'error': 'No tienes permiso para ver esta transacción'}), 403

        include_sensitive = current_user.is_admin if hasattr(current_user, 'is_admin') else False

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(include_sensitive=include_sensitive),
        }), 200

    except Exception as e:
        print(f'❌ Error obteniendo detalle de transacción: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@history_member_bp.route('/stats', methods=['GET'])
@login_required
def api_get_history_stats():
    """API endpoint para obtener estadísticas del historial del usuario."""
    try:
        from app import HistoryTransaction

        transactions = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id == current_user.id)
            | (HistoryTransaction.visibility.in_(['user', 'both']))
        ).all()

        type_counts = Counter(t.transaction_type for t in transactions)
        status_counts = Counter(t.status for t in transactions)

        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = HistoryTransaction.query.filter(
            (HistoryTransaction.owner_user_id == current_user.id)
            | (HistoryTransaction.visibility.in_(['user', 'both'])),
            HistoryTransaction.timestamp >= week_ago,
        ).count()

        return jsonify({
            'success': True,
            'stats': {
                'total': len(transactions),
                'recent_7_days': recent_count,
                'by_type': dict(type_counts),
                'by_status': dict(status_counts),
            },
        }), 200

    except Exception as e:
        print(f'❌ Error obteniendo estadísticas de historial: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
