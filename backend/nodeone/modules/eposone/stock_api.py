"""Helpers API EPosOne — inventario (Etapa 7 slice 14b)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.stock import StockValidationError


def stock_adjust_handler(gate: int):
    body = request.get_json(silent=True) or {}
    try:
        from nodeone.core.platform.connected_inventory import record_connected_adjust

        dto = record_connected_adjust(gate, body, source_app_id='eposone', source_system='EP1')
    except (StockValidationError, OrderValidationError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'stock_balance': dto.to_dict()}), 201
