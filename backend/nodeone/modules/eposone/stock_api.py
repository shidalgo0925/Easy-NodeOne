"""Helpers API EPosOne — inventario (Etapa 7 slice 14b)."""

from __future__ import annotations

from flask import jsonify, request

from nodeone.core.commerce.order import OrderValidationError
from nodeone.core.commerce.stock import StockService, StockValidationError


def stock_adjust_handler(gate: int):
    body = request.get_json(silent=True) or {}
    try:
        dto = StockService.record_manual_adjust(gate, body, source_app_id='eposone')
    except (StockValidationError, OrderValidationError) as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'stock_balance': dto.to_dict()}), 201
